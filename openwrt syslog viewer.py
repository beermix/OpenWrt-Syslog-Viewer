import sys
import socket
import re
import ctypes
import json
import os
import html
import queue
import functools
import time
import subprocess
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTableWidget,
                             QTableWidgetItem, QHeaderView, QVBoxLayout,
                             QWidget, QMenu, QPushButton, QHBoxLayout, QLabel,
                             QSystemTrayIcon, QLineEdit, QComboBox, QCheckBox, QFrame,
                             QStyledItemDelegate, QStyle, QStyleOptionViewItem, QFileDialog)
from PyQt6.QtCore import QThread, Qt, QTimer, QSize, QRectF, QPointF, QByteArray
from PyQt6.QtGui import (QColor, QCursor, QIcon, QPainter,
                         QPixmap, QFont, QFontMetrics, QTextDocument, 
                         QAbstractTextDocumentLayout, QPen, QTextOption,
                         QKeySequence, QShortcut)

# --- CONFIGURATION ---
LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 514

UI_FONT_NAME = "Segoe UI"
UI_FONT_SIZE = 10

LOG_FONT_MONO = "'Cascadia Code', 'Consolas', 'Courier New', monospace"
LOG_FONT_MONO_SIZE = 10
LOG_FONT_MSG = "Tahoma"
LOG_FONT_MSG_SIZE = 9

MAX_ROWS = 10000

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(application_path, "config.json")

# --- WINDOWS AUTOSTART HELPERS ---
def get_windows_startup_dir() -> str:
    if sys.platform == 'win32':
        appdata = os.environ.get('APPDATA', '')
        if appdata:
            return os.path.join(appdata, r'Microsoft\Windows\Start Menu\Programs\Startup')
    return ""

def is_windows_autostart_active() -> bool:
    startup_dir = get_windows_startup_dir()
    if not startup_dir or not os.path.exists(startup_dir):
        return False
    lnk = os.path.join(startup_dir, "OpenWrt Syslog Viewer.lnk")
    bat = os.path.join(startup_dir, "run_openwrt_syslog_viewer.bat")
    return os.path.exists(lnk) or os.path.exists(bat)

def set_windows_autostart(enable: bool) -> bool:
    if sys.platform != 'win32':
        return False
    startup_dir = get_windows_startup_dir()
    if not startup_dir or not os.path.exists(startup_dir):
        return False

    lnk_path = os.path.join(startup_dir, "OpenWrt Syslog Viewer.lnk")
    bat_in_startup = os.path.join(startup_dir, "run_openwrt_syslog_viewer.bat")

    if enable:
        if getattr(sys, 'frozen', False):
            target_file = sys.executable
        else:
            target_file = os.path.join(application_path, "run_openwrt_syslog_viewer.bat")
            if not os.path.exists(target_file):
                target_file = sys.executable

        ps_script = (
            f"$ws = New-Object -ComObject WScript.Shell; "
            f"$s = $ws.CreateShortcut('{lnk_path}'); "
            f"$s.TargetPath = '{target_file}'; "
            f"$s.WorkingDirectory = '{application_path}'; "
            f"$s.WindowStyle = 7; "
            f"$s.Description = 'OpenWrt Syslog Viewer'; "
            f"$s.Save()"
        )
        try:
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                creationflags=flags,
                check=True,
                timeout=5
            )
            return os.path.exists(lnk_path)
        except Exception as e:
            print(f"Error setting autostart: {e}")
            return False
    else:
        try:
            if os.path.exists(lnk_path):
                os.remove(lnk_path)
            if os.path.exists(bat_in_startup):
                os.remove(bat_in_startup)
            return True
        except Exception as e:
            print(f"Error removing autostart: {e}")
            return False

# --- PRE-COMPILED REGEXES ---
RE_PRI = re.compile(r'^<(\d+)>')
# Strip any bracketed timestamp like [29 июл. 2026 г., 16:39:12 GMT+3]
RE_DATE_BRACKET = re.compile(r'^\[[^\]]*\d{2}:\d{2}[^\]]*\]\s*') 
# Strip standard Syslog formats, optional day of week, optional year
RE_DATE_SYSLOG = re.compile(r'^(?:[A-Z][a-z]{2}\s+)?([A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2}(?:\s+\d{4})?)\s*', re.IGNORECASE)
# Strip ISO timestamps
RE_DATE_ISO = re.compile(r'^\d{4}[-/]\d{2}[-/]\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?\s*')

RE_FACILITY_SEV = re.compile(r'^([a-z0-9]+)\.(emerg|alert|crit|err|error|warn|warning|notice|info|debug|dbug)[:\s]\s*', re.IGNORECASE)
RE_HOSTNAME = re.compile(r'^([a-zA-Z0-9_\-]+)\s+(?!:)')
RE_COMP = re.compile(r'^([a-zA-Z0-9_\-\.]+)(?:\[\d+\])?:\s*')
RE_INNER_DATE = re.compile(r'^\d{4}[-/]\d{2}[-/]\d{2}[\sT]\d{2}:\d{2}:\d{2}(?:\.\d+)?\s*')
RE_APP_LVL = re.compile(r'^(?:\[(emerg|alert|crit|err|error|warn|warning|notice|info|debug|dbug)\]|(emerg|alert|crit|err|error|warn|warning|notice|info|debug|dbug)(?:\[\d+\]|\s*:))\s*', re.IGNORECASE)

RE_ANSI = re.compile(r'\x1B\[([\d;]*)m')

HIGHLIGHT_WORDS = {
    "error": "#ff4d4f",
    "failed": "#ff4d4f",
    "failure": "#ff4d4f",
    "warning": "#ffd24d",
    "timeout": "#ff7875",
    "refused": "#ff7875",
    "denied": "#ff7875"
}

HIGHLIGHT_REGEXES = [
    (re.compile(rf'\b({re.escape(w)})\b', re.IGNORECASE), color) 
    for w, color in HIGHLIGHT_WORDS.items()
]

# --- PALETTE ---
LEVEL_BADGE = {
    "EMERG": ((255, 77, 79, 35), "#ff4d4f"), 
    "ALERT": ((255, 120, 117, 35), "#ff7875"),
    "CRIT":  ((244, 135, 113, 35), "#f48771"), 
    "ERR":   ((244, 135, 113, 35), "#f48771"),
    "WARN":  ((255, 210, 77, 35), "#ffd24d"), 
    "NOTE":  ((152, 195, 121, 35), "#98c379"),
    "INFO":  ((111, 182, 255, 35), "#6fb6ff"), 
    "DBUG":  ((154, 154, 154, 35), "#9a9a9a"),
    "UNK":   ((192, 132, 252, 35), "#c084fc"),
}

LVL_MAP_STR = {
    'emerg': 'EMERG', 'alert': 'ALERT', 'crit': 'CRIT',
    'err': 'ERR', 'error': 'ERR', 'warn': 'WARN', 'warning': 'WARN',
    'notice': 'NOTE', 'info': 'INFO', 'debug': 'DBUG', 'dbug': 'DBUG'
}


# --- FILTER SNAPSHOT CLASS ---
class FilterSnapshot:
    def __init__(self, proc_text: str, not_proc: bool,
                 msg_text: str, not_msg: bool, quick_proc: str, active: bool):
        self.proc_keywords = [k.strip().lower() for k in proc_text.split(',') if k.strip()] if proc_text else []
        self.not_proc = not_proc
        self.msg_keywords = [k.strip().lower() for k in msg_text.split(',') if k.strip()] if msg_text else []
        self.not_msg = not_msg
        self.quick_proc = quick_proc
        self.active = active

    def matches(self, proc: str, raw_msg: str) -> bool:
        if not self.active: return True
        if self.quick_proc and proc != self.quick_proc: return False
            
        proc_lower = proc.lower()
        if self.proc_keywords:
            match = any(k in proc_lower for k in self.proc_keywords)
            if self.not_proc: match = not match
            if not match: return False

        raw_lower = raw_msg.lower()
        if self.msg_keywords:
            match = any(k in raw_lower for k in self.msg_keywords)
            if self.not_msg: match = not match
            if not match: return False

        return True


# --- LOG LINE DELEGATE ---
class LogLineDelegate(QStyledItemDelegate):
    PAD_X = 6
    PAD_Y = 4

    def __init__(self, parent=None, viewer=None):
        super().__init__(parent)
        self.viewer = viewer

    def _proc_color(self, comp):
        if comp and "kernel" in comp.lower():
            return "#4ec9b0"
        return "#cfcfcf"

    def _build_doc_internal(self, text, col, selected):
        fg = "#ffffff" if selected else "#e0e0e0"
        fs_mono = LOG_FONT_MONO_SIZE
        fs_msg = LOG_FONT_MSG_SIZE
        mono = LOG_FONT_MONO
        msg_font = LOG_FONT_MSG
        
        if col == 0:
            body = f"<div style='color:{'#9fd0ff' if selected else '#6e8ba8'}; font-family:{mono}; font-size:{fs_mono}pt; white-space: nowrap; text-align: center;'>{text}</div>"
        elif col == 1:
            body = ""
        elif col == 2:
            color = self._proc_color(text)
            body = f"<div style='color:{color}; font-family:{mono}; font-size:{fs_mono}pt; white-space: nowrap;'>{text}</div>"
        else:
            body = f"<div style='color:{fg}; font-family:{msg_font}; font-size:{fs_msg}pt; margin:0; line-height: 1.3; white-space: pre-wrap; word-wrap: break-word;'>{text}</div>"
            
        doc = QTextDocument()
        doc.setHtml(body)
        
        font = QFont()
        if col == 3:
            font.setFamily(msg_font)
            font.setPointSize(fs_msg)
        else:
            font.setFamily("Consolas")
            font.setPointSize(fs_mono)
        doc.setDefaultFont(font)
        
        option = doc.defaultTextOption()
        if col == 3:
            option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        else:
            option.setWrapMode(QTextOption.WrapMode.NoWrap)
        doc.setDefaultTextOption(option)
        return doc

    @functools.lru_cache(maxsize=10000)
    def _get_doc_height(self, text, width) -> int:
        doc = self._build_doc_internal(text, 3, False)
        doc.setTextWidth(max(width - 2 * self.PAD_X, 1))
        return int(doc.size().height()) + 2 * self.PAD_Y

    def paint(self, painter, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        style = options.widget.style() if options.widget else QApplication.style()
        col = index.column()

        options.text = ""
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, options, painter, options.widget)
        textRect = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, options)

        selected = bool(options.state & QStyle.StateFlag.State_Selected)
        hovered = bool(options.state & QStyle.StateFlag.State_MouseOver)

        if selected:
            painter.fillRect(textRect, QColor("#1a3857"))
        else:
            row = index.row()
            if hovered:
                painter.fillRect(textRect, QColor("#242426"))
            elif row % 2 == 1:
                painter.fillRect(textRect, QColor("#1c1c1e"))
            else:
                painter.fillRect(textRect, QColor("#1f1f1f"))

        if col < 3:
            painter.save()
            painter.setPen(QPen(QColor("#2a2a2a"), 1))
            x = textRect.right() - 0.5
            painter.drawLine(QPointF(x, textRect.top()), QPointF(x, textRect.bottom()))
            painter.restore()

        inner = textRect.adjusted(self.PAD_X, self.PAD_Y, -self.PAD_X, -self.PAD_Y)

        if col == 1:
            lvl = (index.data(Qt.ItemDataRole.DisplayRole) or "").strip()
            bg_rgba, fg_hex = LEVEL_BADGE.get(lvl, LEVEL_BADGE["UNK"])
            
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            
            painter.setBrush(QColor(*bg_rgba))
            painter.setPen(Qt.PenStyle.NoPen)
            
            font = QFont(UI_FONT_NAME, 9)
            font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            
            fm = painter.fontMetrics()
            label = lvl[:4]
            tw = fm.horizontalAdvance(label)
            th = fm.height()
            
            badge_w = tw + 14
            badge_h = th + 4
            bx = inner.left() + (inner.width() - badge_w) / 2
            by = textRect.top() + (textRect.height() - badge_h) / 2
                
            painter.drawRoundedRect(QRectF(bx, by, badge_w, badge_h), 4, 4)
            painter.setPen(QColor(fg_hex))
            painter.drawText(QRectF(bx, by, badge_w, badge_h), Qt.AlignmentFlag.AlignCenter, label)
            painter.restore()
            return

        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        doc = self._build_doc_internal(text, col, selected)
        doc.setTextWidth(inner.width())
        
        doc_height = doc.size().height()
        available_height = textRect.height()
        y_offset = max(0.0, (available_height - doc_height) / 2.0)

        ctx = QAbstractTextDocumentLayout.PaintContext()
        painter.save()
        painter.translate(inner.left(), textRect.top() + y_offset)
        painter.setClipRect(QRectF(0, 0, inner.width(), doc_height))
        doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(self, option, index):
        table = self.parent()
        width = table.columnWidth(index.column()) if table is not None else 100
        col = index.column()
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        
        if col == 3:
            h = self._get_doc_height(text, width)
            return QSize(width, max(26, h))
        else:
            font = QFont("Consolas", LOG_FONT_MONO_SIZE)
            fm = QFontMetrics(font)
            
            if col == 1:
                font.setWeight(QFont.Weight.Bold)
                fm_badge = QFontMetrics(font)
                w = fm_badge.horizontalAdvance(text[:4]) + 24 + 2 * self.PAD_X
            else:
                extra = 10 if col == 0 else 16
                w = fm.horizontalAdvance(text) + 2 * self.PAD_X + extra
                
            h = fm.height() + 2 * self.PAD_Y
            return QSize(int(w), max(26, h))


# --- ANSI PARSER ---
def ansi_to_html(text):
    colors = {
        '30': '#a0a0a0', '31': '#ff8b94', '32': '#a8e6cf', '33': '#ffd3b6', '34': '#6fb1fc', 
        '35': '#d8b4e2', '36': '#a2dfe3', '37': '#ffffff', 
        '90': '#bbbbbb', '91': '#ffaaa5', '92': '#c1f0dc', '93': '#ffead2', 
        '94': '#8ec5fc', '95': '#e0c3fc', '96': '#befcff', '97': '#ffffff',
    }
    def replace_match(match):
        code = match.group(1)
        if code == '0' or code == '': return '</span>'
        parts = code.split(';')
        color_hex = None
        for part in parts:
            if part in colors: color_hex = colors[part]
        if color_hex: return f'<span style="color:{color_hex}">'
        return ''

    html_text = RE_ANSI.sub(replace_match, text)
    html_text = html_text.replace('\n', '<br>')
    return html_text


# --- ICON ---
def create_app_icon():
    ico_path = os.path.join(application_path, "app_icon.ico")
    if os.path.exists(ico_path):
        icon = QIcon(ico_path)
        if not icon.isNull():
            return icon

    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor("transparent"))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#1e1e1e"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, 64, 64, 14, 14)
    painter.setPen(QColor("#4ec9b0"))
    painter.setFont(QFont(UI_FONT_NAME, 26, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, ">_")
    painter.end()
    return QIcon(pixmap)


# --- WORKER THREADS ---
class UdpReceiverThread(QThread):
    def __init__(self, raw_queue, parent=None):
        super().__init__(parent)
        self.raw_queue = raw_queue
        self.sock = None

    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if os.name == 'nt':
            try: self.sock.ioctl(socket.SIO_UDP_CONNRESET, False)
            except Exception: pass

        try:
            self.sock.bind((LISTEN_IP, LISTEN_PORT))
        except Exception as e:
            self.raw_queue.put(b"SOCKET_ERROR: " + str(e).encode())
            return

        self.sock.settimeout(1.0)
        while not self.isInterruptionRequested():
            try:
                data, addr = self.sock.recvfrom(65535)
                self.raw_queue.put(data)
            except socket.timeout: continue
            except OSError as e:
                if getattr(e, 'winerror', None) == 10054: continue
            except Exception: pass
            
        self.sock.close()


class LogParserThread(QThread):
    def __init__(self, raw_queue, gui_queue, parent=None):
        super().__init__(parent)
        self.raw_queue = raw_queue
        self.gui_queue = gui_queue

    def run(self):
        while not self.isInterruptionRequested():
            try:
                data = self.raw_queue.get(timeout=0.5)
                if data.startswith(b"SOCKET_ERROR: "):
                    err_msg = data.decode('utf-8', errors='replace')
                    self.gui_queue.put(("", "CRIT", "SYS", err_msg, err_msg))
                    continue

                raw_msg = data.decode('utf-8', errors='replace')
                self.parse_syslog(raw_msg)
            except queue.Empty:
                continue

    def parse_syslog(self, raw_msg):
        msg_body = raw_msg

        # 1. Syslog PRI (если есть)
        pri_match = RE_PRI.search(msg_body)
        priority = 13
        if pri_match:
            priority = int(pri_match.group(1))
            msg_body = msg_body[pri_match.end():]

        severity = priority & 7
        lvl_map = {0: "EMERG", 1: "ALERT", 2: "CRIT", 3: "ERR", 4: "WARN", 5: "NOTE", 6: "INFO", 7: "DBUG"}
        level = lvl_map.get(severity, "UNK")

        msg_body = msg_body.strip()
        timestamp = datetime.now().strftime("%H:%M:%S")

        # 2. Очистка различных форматов даты (syslog date, ISO 8601, bracket format)
        msg_body = RE_DATE_BRACKET.sub('', msg_body)
        msg_body = RE_DATE_SYSLOG.sub('', msg_body)
        msg_body = RE_DATE_ISO.sub('', msg_body)

        # 3. Парсинг facility.severity (например daemon.notice)
        fac_match = RE_FACILITY_SEV.match(msg_body)
        if fac_match:
            fac_sev = fac_match.group(2).lower()
            level = LVL_MAP_STR.get(fac_sev, level)
            msg_body = msg_body[fac_match.end():]

        # 4. Пропуск имени хоста (если присутствует перед компонентом)
        host_match = RE_HOSTNAME.match(msg_body)
        if host_match:
            if not RE_COMP.match(msg_body):
                msg_body = msg_body[host_match.end():]

        # 5. Парсинг имени компонента/процесса
        comp_match = RE_COMP.match(msg_body)
        if comp_match:
            component = comp_match.group(1)
            msg_body = msg_body[comp_match.end():]
        else:
            component = "kernel" if "kernel" in msg_body.lower() else "sys"

        # 6. Очистка дублирующихся внутренних таймстемпов приложений (AdGuardHome, torrserver)
        msg_body = RE_INNER_DATE.sub('', msg_body)

        # 7. Приоритетный парсинг внутренних уровней приложения (например [info] или ERROR[123])
        app_lvl_match = RE_APP_LVL.match(msg_body)
        if app_lvl_match:
            app_sev = (app_lvl_match.group(1) or app_lvl_match.group(2)).lower()
            level = LVL_MAP_STR.get(app_sev, level)
            if app_lvl_match.group(1):
                msg_body = msg_body[app_lvl_match.end():]

        raw_message_text = msg_body.strip()

        # 8. Эвристики для специфичного поведения OpenWrt / BusyBox:
        # a) crond: штатный запуск заданий BusyBox логирует с LOG_ERR (cron.err)
        if component.lower() == "crond" and level == "ERR" and raw_message_text.startswith("USER ") and " cmd " in raw_message_text:
            level = "INFO"

        # b) torrserver: Go пишет логи в stderr, procd помечает как daemon.err
        if component.lower() == "torrserver" and level == "ERR":
            if not re.search(r'\b(error|failed|failure|panic|fatal)\b', raw_message_text, re.IGNORECASE):
                level = "INFO"

        # c) Сетевые события падения линка -> предупреждение (WARN)
        if level in ("NOTE", "INFO") and re.search(r'\blink is down\b', raw_message_text, re.IGNORECASE):
            level = "WARN"

        escaped_text = html.escape(raw_message_text, quote=False)
        for pattern, color in HIGHLIGHT_REGEXES:
            escaped_text = pattern.sub(rf'<span style="color:{color}; font-weight:bold;">\1</span>', escaped_text)
            
        html_message = ansi_to_html(escaped_text)
        self.gui_queue.put((timestamp, level, component, html_message, raw_message_text))


# --- GUI ---
class CompactLogViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.filters_active = True
        self.quick_filter_proc = None
        self.start_minimized_flag = False
        self._is_quitting = False
        self._last_alert_time = 0.0

        self.save_config_timer = QTimer(self)
        self.save_config_timer.setSingleShot(True)
        self.save_config_timer.setInterval(500)
        self.save_config_timer.timeout.connect(self.save_config)

        self.app_icon = create_app_icon()
        self.setWindowIcon(self.app_icon)
        self.setWindowTitle(f"OpenWrt Log Monitor : {LISTEN_PORT}")
        self.resize(1300, 800)

        self.setup_tray()
        self.setStyleSheet(self.build_stylesheet())
        self.apply_dark_titlebar()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. TOOLBAR
        toolbar_container = QWidget()
        toolbar_container.setObjectName("Toolbar")
        toolbar = QHBoxLayout(toolbar_container)
        toolbar.setContentsMargins(10, 6, 10, 6)
        toolbar.setSpacing(10)
        
        self.btn_pause = QPushButton("Pause")
        self.btn_pause.setObjectName("PauseBtn")
        self.btn_pause.setCheckable(True)
        
        self.btn_copy_all = QPushButton("Copy All")
        self.btn_copy_all.clicked.connect(self.copy_all_logs)
        
        self.btn_export = QPushButton("Export")
        self.btn_export.clicked.connect(self.export_logs)
        
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self.clear_logs)
        
        self.btn_autoscroll = QPushButton("Auto Scroll")
        self.btn_autoscroll.setCheckable(True)
        self.btn_autoscroll.setChecked(True)
        self.btn_autoscroll.clicked.connect(self.save_config)
        
        self.chk_start_min = QCheckBox("Start in Tray")
        self.chk_start_min.stateChanged.connect(self.save_config)

        self.chk_autostart = QCheckBox("Auto-start")
        self.chk_autostart.setToolTip("Запуск при старте Windows (run_openwrt_syslog_viewer.bat)")
        self.chk_autostart.stateChanged.connect(self.on_autostart_changed)

        self.btn_exit = QPushButton("Exit")
        self.btn_exit.setObjectName("ExitBtn")
        self.btn_exit.clicked.connect(self.quit_app)

        self.status_label = QLabel("● Ready")
        self.status_label.setObjectName("StatusLabel")

        toolbar.addWidget(self.btn_pause)
        toolbar.addWidget(self.btn_copy_all)
        toolbar.addWidget(self.btn_export)
        toolbar.addWidget(self.btn_clear)
        toolbar.addWidget(self.btn_autoscroll)
        toolbar.addWidget(self.chk_start_min)
        toolbar.addWidget(self.chk_autostart)
        toolbar.addWidget(self.btn_exit)
        toolbar.addStretch()
        toolbar.addWidget(self.status_label)
        
        main_layout.addWidget(toolbar_container)

        # 2. FILTER & ALERT BAR
        filter_frame = QFrame()
        filter_frame.setObjectName("FilterFrame")
        frame_layout = QVBoxLayout(filter_frame)
        frame_layout.setContentsMargins(10, 6, 10, 6)
        frame_layout.setSpacing(0)

        row_filters = QHBoxLayout()
        row_filters.setSpacing(8)
        
        self.btn_toggle_filters = QPushButton("Filters: ON")
        self.btn_toggle_filters.setObjectName("ToggleFilters")
        self.btn_toggle_filters.setCheckable(True)
        self.btn_toggle_filters.setChecked(True)
        self.btn_toggle_filters.setFixedWidth(90)
        self.btn_toggle_filters.clicked.connect(self.toggle_filters_state)
        
        self.btn_quick_filter = QPushButton()
        self.btn_quick_filter.setObjectName("QuickFilterBtn")
        self.btn_quick_filter.setVisible(False)
        self.btn_quick_filter.clicked.connect(self.clear_quick_filter)
        
        self.chk_not_proc = QCheckBox("!")
        self.chk_not_proc.stateChanged.connect(self.on_config_changed)
        
        self.inp_proc = QLineEdit()
        self.inp_proc.setPlaceholderText("Process...")
        self.inp_proc.textChanged.connect(self.on_config_changed)

        self.chk_not_msg = QCheckBox("!")
        self.chk_not_msg.stateChanged.connect(self.on_config_changed)
        
        self.inp_msg = QLineEdit()
        self.inp_msg.setPlaceholderText("Message...")
        self.inp_msg.textChanged.connect(self.on_config_changed)

        lbl_alert = QLabel("🔔 Alert:")
        lbl_alert.setStyleSheet("color: #b0b0b0; font-weight: bold; margin-left: 8px;")
        
        self.inp_alert = QLineEdit()
        self.inp_alert.setObjectName("AlertInput")
        self.inp_alert.setPlaceholderText("Keywords...")
        self.inp_alert.setMaximumWidth(150)
        self.inp_alert.textChanged.connect(self.on_alert_changed)

        row_filters.addWidget(self.btn_toggle_filters)
        row_filters.addWidget(self.btn_quick_filter)
        row_filters.addWidget(QLabel("Proc:"))
        row_filters.addWidget(self.chk_not_proc)
        row_filters.addWidget(self.inp_proc)
        row_filters.addWidget(QLabel("Msg:"))
        row_filters.addWidget(self.chk_not_msg)
        row_filters.addWidget(self.inp_msg)
        row_filters.addWidget(lbl_alert)
        row_filters.addWidget(self.inp_alert)
        
        frame_layout.addLayout(row_filters)
        main_layout.addWidget(filter_frame)

        # 3. TABLE
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["TIME", "LVL", "PROC", "MESSAGE"])
        h = self.table.horizontalHeader()
        
        h.setFixedHeight(24)
        
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        h.setStretchLastSection(True)

        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(26) 
        self.table.setMouseTracking(True)
        self.table.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.cellClicked.connect(self.on_cell_clicked)
        
        self.copy_shortcut = QShortcut(QKeySequence.StandardKey.Copy, self.table)
        self.copy_shortcut.activated.connect(self.copy_selection)
        
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(150)
        self._resize_timer.timeout.connect(self.update_rows_height)
        self.table.horizontalHeader().sectionResized.connect(self._resize_timer.start)

        self._log_delegate = LogLineDelegate(self.table, viewer=self)
        for col in range(self.table.columnCount()):
            self.table.setItemDelegateForColumn(col, self._log_delegate)

        main_layout.addWidget(self.table)
        
        self.filter_timer = QTimer(self)
        self.filter_timer.setSingleShot(True)
        self.filter_timer.setInterval(300)
        self.filter_timer.timeout.connect(self.apply_filters)

        self.raw_queue = queue.Queue()
        self.gui_queue = queue.Queue()
        
        self.udp_thread = UdpReceiverThread(self.raw_queue)
        self.parser_thread = LogParserThread(self.raw_queue, self.gui_queue)
        
        self.load_config()
        self.on_alert_changed() 
        
        self.table.setFont(QFont(UI_FONT_NAME, UI_FONT_SIZE))
        
        self.udp_thread.start()
        self.parser_thread.start()

        self.ui_update_timer = QTimer(self)
        self.ui_update_timer.timeout.connect(self.process_log_queue)
        self.ui_update_timer.start(100)

    def get_filter_snapshot(self) -> FilterSnapshot:
        return FilterSnapshot(
            proc_text=self.inp_proc.text(),
            not_proc=self.chk_not_proc.isChecked(),
            msg_text=self.inp_msg.text(),
            not_msg=self.chk_not_msg.isChecked(),
            quick_proc=self.quick_filter_proc,
            active=self.filters_active
        )

    # --- LOGIC ---
    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self.app_icon, self)
        menu = QMenu()
        menu.setStyleSheet("QMenu { background-color: #1e1e1e; color: #f0f0f0; }")
        menu.addAction("Restore / Minimize", self.toggle_window_state)
        menu.addAction("Exit", self.quit_app)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def quit_app(self):
        self._is_quitting = True
        self.save_config()
        self.udp_thread.requestInterruption()
        self.parser_thread.requestInterruption()
        self.udp_thread.wait(1000)
        self.parser_thread.wait(1000)
        QApplication.instance().quit()

    def apply_dark_titlebar(self):
        if sys.platform != "win32": return
        try:
            hwnd = int(self.winId())
            if not hwnd: return
            for attr in (20, 19):
                r = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attr, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int))
                if r == 0: break
        except Exception: pass

    def on_tray_icon_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.toggle_window_state()

    def toggle_window_state(self):
        if self.isVisible() and not self.isMinimized(): self.minimize_to_tray()
        else: self.restore_window()
        
    def minimize_to_tray(self): self.hide()
    def restore_window(self): self.showNormal(); self.activateWindow(); self.raise_()
    
    def showEvent(self, event):
        super().showEvent(event)
        self.apply_dark_titlebar()

    def clear_logs(self):
        self.table.setRowCount(0)
        self._log_delegate._get_doc_height.cache_clear()
        while not self.gui_queue.empty():
            try: self.gui_queue.get_nowait()
            except queue.Empty: break
        self.status_label.setText("● Logs: 0")

    def on_alert_changed(self):
        if self.inp_alert.text().strip():
            self.inp_alert.setStyleSheet("QLineEdit#AlertInput { border: 1px solid #b34747; background-color: #3b2525; }")
        else:
            self.inp_alert.setStyleSheet("") 
        self.save_config_timer.start()

    def apply_filters(self):
        filters = self.get_filter_snapshot()
        self.table.setUpdatesEnabled(False)
        for row in range(self.table.rowCount()):
            proc_item = self.table.item(row, 2)
            msg_item = self.table.item(row, 3)
            if not proc_item or not msg_item:
                continue
            proc = proc_item.text()
            raw_msg = msg_item.data(Qt.ItemDataRole.UserRole) or ""
            
            is_visible = filters.matches(proc, raw_msg)
            self.table.setRowHidden(row, not is_visible)
            
        self.table.resizeColumnToContents(0)
        self.table.resizeColumnToContents(1)
        self.table.resizeColumnToContents(2)
        self.table.setUpdatesEnabled(True)
        
        self.update_rows_height()
        
        if self.btn_autoscroll.isChecked():
            QTimer.singleShot(0, self.table.scrollToBottom)

    def toggle_filters_state(self):
        self.filters_active = self.btn_toggle_filters.isChecked()
        self.btn_toggle_filters.setText("Filters: ON" if self.filters_active else "Filters: OFF")
        self.apply_filters()

    def check_alert(self, level, comp, raw_msg):
        alert_str = self.inp_alert.text()
        if alert_str:
            clean_msg = raw_msg.lower()
            clean_comp = comp.lower()
            keywords = [k.strip().lower() for k in alert_str.split(',') if k.strip()]
            for k in keywords:
                if k in clean_msg or k in clean_comp: return True, f"ALERT: {k.upper()} detected"
        return False, ""

    def update_rows_height(self):
        col3_width = max(self.table.columnWidth(3), 200)
        approx_char_width = 8
        max_single_line_chars = int(col3_width / approx_char_width)

        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                msg_item = self.table.item(row, 3)
                if not msg_item:
                    continue
                raw_msg = msg_item.data(Qt.ItemDataRole.UserRole) or ""
                html_msg = msg_item.text()
                if len(raw_msg) < max_single_line_chars:
                    h = 26
                else:
                    h = max(26, self._log_delegate._get_doc_height(html_msg, col3_width))
                self.table.setRowHeight(row, h)
                
        self.table.blockSignals(False)
        self.table.setUpdatesEnabled(True)

    def process_log_queue(self):
        if self.gui_queue.empty() or self.btn_pause.isChecked(): 
            return
            
        records = []
        while not self.gui_queue.empty():
            records.append(self.gui_queue.get())
            if len(records) >= 1000: break
                
        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        
        col3_width = max(self.table.columnWidth(3), 200)
        approx_char_width = 8
        max_single_line_chars = int(col3_width / approx_char_width)
        
        filters = self.get_filter_snapshot()
        
        for time_str, level, comp, html_msg, raw_msg in records:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            i_time = QTableWidgetItem(time_str)
            i_time.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            
            i_lvl = QTableWidgetItem(level)
            i_lvl.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            
            i_comp = QTableWidgetItem(comp)
            i_comp.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            
            i_msg = QTableWidgetItem(html_msg)
            i_msg.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            i_msg.setData(Qt.ItemDataRole.UserRole, raw_msg)
            
            self.table.setItem(row, 0, i_time)
            self.table.setItem(row, 1, i_lvl)
            self.table.setItem(row, 2, i_comp)
            self.table.setItem(row, 3, i_msg)

            if len(raw_msg) < max_single_line_chars:
                h = 26
            else:
                h = max(26, self._log_delegate._get_doc_height(html_msg, col3_width))
            self.table.setRowHeight(row, h)

            is_visible = filters.matches(comp, raw_msg)
            if not is_visible:
                self.table.setRowHidden(row, True)

            if is_visible or not filters.active:
                should_alert, title = self.check_alert(level, comp, raw_msg)
                if should_alert: 
                    now = time.time()
                    if now - self._last_alert_time >= 2.0:
                        self._last_alert_time = now
                        self.tray_icon.showMessage(title, f"{comp}: {raw_msg[:100]}", QSystemTrayIcon.MessageIcon.Warning, 3000)

        excess = self.table.rowCount() - MAX_ROWS
        if excess > 500:  
            self.table.model().removeRows(0, excess)
            
        self.table.blockSignals(False)
        self.table.setUpdatesEnabled(True)
        
        self.status_label.setText(f"● Logs: {self.table.rowCount()}")
        self.status_label.setStyleSheet("color: #4ec9b0; font-weight: bold;")
        QTimer.singleShot(500, lambda: self.status_label.setStyleSheet("color: #888888;"))

        if self.btn_autoscroll.isChecked():
            self.table.scrollToBottom()

    def on_cell_clicked(self, row, column):
        if column != 2: return
        item = self.table.item(row, column)
        if not item: return
            
        proc = item.text()
        if self.quick_filter_proc == proc:
            self.clear_quick_filter()
        else:
            self.quick_filter_proc = proc
            self.btn_quick_filter.setText(f"🔍 {proc}  ✖")
            self.btn_quick_filter.setVisible(True)
            self.apply_filters()

    def clear_quick_filter(self):
        self.quick_filter_proc = None
        self.btn_quick_filter.setVisible(False)
        self.apply_filters()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.block_signals_all(True)
                    self.inp_proc.setText(data.get("proc", ""))
                    self.chk_not_proc.setChecked(data.get("not_proc", False))
                    self.inp_msg.setText(data.get("msg", ""))
                    self.chk_not_msg.setChecked(data.get("not_msg", False))
                    self.inp_alert.setText(data.get("alert_keywords", ""))
                    self.btn_autoscroll.setChecked(data.get("autoscroll", True))
                    self.chk_start_min.setChecked(data.get("start_minimized", False))
                    self.start_minimized_flag = data.get("start_minimized", False)
                    
                    geom = data.get("geometry")
                    if geom:
                        self.restoreGeometry(QByteArray.fromBase64(geom.encode('utf-8')))
                        
                    self.block_signals_all(False)
            except Exception: pass

        # Проверяем реальное состояние автозагрузки в Windows при старте программы
        self.chk_autostart.blockSignals(True)
        self.chk_autostart.setChecked(is_windows_autostart_active())
        self.chk_autostart.blockSignals(False)

    def save_config(self):
        data = {
            "proc": self.inp_proc.text(), "not_proc": self.chk_not_proc.isChecked(),
            "msg": self.inp_msg.text(), "not_msg": self.chk_not_msg.isChecked(),
            "alert_keywords": self.inp_alert.text(), "autoscroll": self.btn_autoscroll.isChecked(),
            "start_minimized": self.chk_start_min.isChecked(),
            "geometry": self.saveGeometry().toBase64().data().decode('utf-8')
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception: pass

    def block_signals_all(self, block):
        for w in [self.inp_proc, self.chk_not_proc, self.inp_msg, self.chk_not_msg, 
                  self.inp_alert, self.btn_autoscroll, self.chk_start_min,
                  self.chk_autostart]: 
            w.blockSignals(block)

    def on_autostart_changed(self, state):
        enable = self.chk_autostart.isChecked()
        set_windows_autostart(enable)
        # Синхронизируем с реальным наличием ярлыка в Windows
        actual = is_windows_autostart_active()
        if actual != self.chk_autostart.isChecked():
            self.chk_autostart.blockSignals(True)
            self.chk_autostart.setChecked(actual)
            self.chk_autostart.blockSignals(False)

    def on_config_changed(self): 
        self.save_config_timer.start()
        self.filter_timer.start()

    def build_stylesheet(self):
        fn, fs = UI_FONT_NAME, UI_FONT_SIZE
        return f"""
            QMainWindow {{ background-color: #1f1f1f; }}
            QWidget {{ font-family: '{fn}'; font-size: {fs}pt; }}

            QTableWidget {{
                background-color: #1f1f1f; color: #f0f0f0; border: none;
                outline: 0; gridline-color: transparent;
            }}
            QTableWidget::item {{ padding: 0px; border: none; }}
            QTableWidget::item:focus {{ border: none; outline: none; }}

            QHeaderView {{ border: none; background-color: #252526; }}
            QHeaderView::section {{
                background-color: #252526; color: #a0a0a0;
                border: none; border-bottom: 1px solid #333333;
                border-right: 1px solid #333333;
                padding: 4px 6px; font-weight: bold; text-transform: uppercase;
                font-size: 8pt; 
            }}
            QHeaderView::section:last {{ border-right: none; }}

            QPushButton {{ 
                background-color: #333333; color: #e0e0e0; 
                border: 1px solid #454545; border-radius: 4px; padding: 4px 10px; 
            }}
            QPushButton:hover {{ background-color: #3a3a3c; border-color: #555555; }}
            QPushButton:checked {{ background-color: #1a3857; border-color: #007acc; color: #6fb6ff; }}

            QPushButton#ToggleFilters {{ background-color: #333333; color: #999; border-color: #454545; }}
            QPushButton#ToggleFilters:checked {{ background-color: #1e3a24; border-color: #4ec9b0; color: #4ec9b0; }}
            
            QPushButton#QuickFilterBtn {{ background-color: #1a3857; color: #6fb6ff; border: 1px solid #007acc; border-radius: 10px; padding: 2px 8px; font-weight: bold; }}
            QPushButton#QuickFilterBtn:hover {{ background-color: #007acc; color: white; }}
            
            QPushButton#PauseBtn:checked {{ background-color: #4a1c1c; border-color: #ff4d4f; color: #ff4d4f; font-weight: bold; }}
            QPushButton#ExitBtn {{ background-color: #332222; color: #ff8b8b; border: 1px solid #553333; }}
            QPushButton#ExitBtn:hover {{ background-color: #4d2626; border-color: #884444; color: #ffffff; }}

            QFrame#FilterFrame {{ background-color: #252526; border-bottom: 1px solid #333333; }}
            QWidget#Toolbar {{ background-color: #252526; border-bottom: 1px solid #333333; }}
            
            QLineEdit, QComboBox {{ 
                background-color: #2d2d30; color: white; 
                border: 1px solid #454545; border-radius: 4px; padding: 2px 6px; 
            }}
            QLineEdit:focus, QComboBox:focus {{ border: 1px solid #007acc; background-color: #333333; }}
            
            QCheckBox {{ color: #b0b0b0; spacing: 6px; }}
            
            QLabel {{ color: #a0a0a0; }}
            QLabel#StatusLabel {{ color: #888888; font-weight: bold; }}
        """

    def export_logs(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Logs", "", "Text Files (*.txt);;All Files (*)")
        if not path: return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                for r in range(self.table.rowCount()):
                    if not self.table.isRowHidden(r):
                        time_item = self.table.item(r, 0)
                        lvl_item = self.table.item(r, 1)
                        proc_item = self.table.item(r, 2)
                        msg_item = self.table.item(r, 3)
                        if time_item and proc_item and msg_item:
                            time_str = time_item.text()
                            lvl_str = lvl_item.text() if lvl_item else ""
                            proc_str = proc_item.text()
                            raw_msg = msg_item.data(Qt.ItemDataRole.UserRole) or ""
                            f.write(f"{time_str} [{lvl_str}] {proc_str}: {raw_msg}\n")
        except Exception as e:
            self.status_label.setText(f"Export error: {e}")

    def copy_all_logs(self): 
        rows = self.table.rowCount()
        text = []
        for r in range(rows):
            if not self.table.isRowHidden(r):
                time_item = self.table.item(r, 0)
                lvl_item = self.table.item(r, 1)
                proc_item = self.table.item(r, 2)
                msg_item = self.table.item(r, 3)
                if time_item and proc_item and msg_item:
                    time_str = time_item.text()
                    lvl_str = lvl_item.text() if lvl_item else ""
                    proc_str = proc_item.text()
                    raw_msg = msg_item.data(Qt.ItemDataRole.UserRole) or ""
                    text.append(f"{time_str} [{lvl_str}] {proc_str}: {raw_msg}")
        QApplication.clipboard().setText("\n".join(text))
        self.btn_copy_all.setText("Copied!")
        QTimer.singleShot(1000, lambda: self.btn_copy_all.setText("Copy All"))

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.addAction("Copy Selection (Ctrl+C)", self.copy_selection)
        menu.exec(QCursor.pos())

    def copy_selection(self):
        ranges = self.table.selectedRanges()
        if not ranges: 
            return
            
        selected_rows = set()
        for r in ranges:
            selected_rows.update(range(r.topRow(), r.bottomRow() + 1))
            
        text = []
        for r in sorted(selected_rows):
            if not self.table.isRowHidden(r):
                time_item = self.table.item(r, 0)
                lvl_item = self.table.item(r, 1)
                proc_item = self.table.item(r, 2)
                msg_item = self.table.item(r, 3)
                if time_item and proc_item and msg_item:
                    time_str = time_item.text()
                    lvl_str = lvl_item.text() if lvl_item else ""
                    proc_str = proc_item.text()
                    raw_msg = msg_item.data(Qt.ItemDataRole.UserRole) or ""
                    text.append(f"{time_str} [{lvl_str}] {proc_str}: {raw_msg}")
                
        QApplication.clipboard().setText("\n".join(text))

    def closeEvent(self, event):
        self.save_config()
        if not self._is_quitting:
            event.ignore()
            self.minimize_to_tray()
        else:
            super().closeEvent(event)


if __name__ == "__main__":
    if sys.platform == "win32" and hasattr(ctypes, "windll"):
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('openwrt.logviewer.classic.v28')
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = CompactLogViewer()
    if window.start_minimized_flag: window.minimize_to_tray()
    else: window.show()
    sys.exit(app.exec())
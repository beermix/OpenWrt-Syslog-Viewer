# OpenWrt Syslog Viewer

<p align="center">
  <img src="pythonw_8KXqwNvxrU.png" alt="OpenWrt Syslog Viewer Screenshot" width="850">
</p>

<p align="center">
  <a href="https://github.com/beermix/OpenWrt-Syslog-Viewer/archive/refs/heads/master.zip">
    <img src="https://img.shields.io/badge/Скачать%20программу-ZIP-success?style=for-the-badge&logo=windows" alt="Скачать программу">
  </a>
</p>

<p align="center">
  <a href="#русский">Русский</a> •
  <a href="#english">English</a>
</p>

---

<a name="русский"></a>
## 🇷🇺 Русский

**OpenWrt Syslog Viewer** — компактный GUI-монитор системных логов OpenWrt в реальном времени.

### 🎯 Назначение
- Приём и отображение логов роутера в реальном времени по UDP (порт 514).
- Фоновая работа в системном трее Windows (`Start in Tray`) с запуском при загрузке системы.
- Оповещение всплывающими сообщениями в трее только при появлении заданных ключевых слов (алертов).
- Полная портативность: файл настроек `config.json` хранится в папке со скриптом.

### ✨ Возможности
- **UDP Syslog (порт 514):** фоновый приём и парсинг форматов RFC 3164 / ISO 8601.
- **Цветовые бейджи:** `EMERG`, `ALERT`, `CRIT`, `ERR`, `WARN`, `NOTE`, `INFO`, `DBUG`.
- **Подсветка синтаксиса:** подсветка `error`, `failed`, `failure`, `timeout`, `refused`, `denied`, `warning` и ANSI-цветов.
- **Умный парсинг OpenWrt:**
  - Автоматическое распознавание штатных запусков `crond` как `INFO` (вместо ложных `ERR`).
  - Фильтрация ложных `ERR` у Go-сервисов (`torrserver`, `sing-box`).
  - Поддержка сервиса `tachyon`: очистка префиксов ядра kmsg, извлечение подмодулей и уровней логирования, выделение цветом.
  - Очистка дублирующихся внутренних дат приложений (AdGuardHome, Go).
  - Повышение приоритета обрывов линка (`link is down`) до `WARN`.
- **Фильтрация:** по процессам (`Proc`) и тексту (`Msg`), поддержка исключений `!`, быстрый фильтр по клику на процесс в таблице.
- **Уведомления в трее:** настраиваемые ключевые слова с защитой от флуда.
- **Экспорт и буфер обмена:** кнопка Copy All, копирование выделения по **Ctrl+C**, экспорт в TXT с сохранением времени и уровней (`LVL`).
- **Тёмная тема:** Dark UI с поддержкой темного заголовка окна Windows 10/11.

### 📦 Установка и запуск (Windows)
1. **Скачайте программу:** **[openwrt-syslog-viewer (ZIP)](https://github.com/beermix/OpenWrt-Syslog-Viewer/archive/refs/heads/master.zip)** и распакуйте в любое место.
2. **Автоматически:** запустите **`install.bat`** (проверит Python, установит `PyQt6`, создаст ярлык на Рабочем столе и предложит добавить в автозагрузку).
3. **Вручную:**
   ```cmd
   pip install PyQt6
   run_openwrt_syslog_viewer.bat
   ```

### 🚀 Автозапуск при загрузке Windows
1. Включите чекбокс **`Auto-start`** в окне программы (или ответьте `Y` при установке через `install.bat`). Программа автоматически создаст ярлык `run_openwrt_syslog_viewer.bat` в автозагрузке Windows.
2. Включите чекбокс **`Start in Tray`**, чтобы при старте системы программа запускалась свёрнутой в трей.

### ⚙️ Настройка роутера OpenWrt
> [!IMPORTANT]
> **Обязательно для работы программы:** чтобы утилита могла принимать и отображать логи, необходимо настроить их отправку с роутера на IP-адрес вашего компьютера.

* **Через LuCI:** **Система** → **Система** → вкладка **Журнал** → указать IP вашего ПК, порт `514`, протокол `UDP`.
* **Через SSH:**
  ```sh
  uci set system.@system[0].log_ip='<IP_ВАШЕГО_ПК>'
  uci set system.@system[0].log_port='514'
  uci set system.@system[0].log_proto='udp'
  uci commit system && /etc/init.d/log restart
  ```

---

<a name="english"></a>
## 🇬🇧 English

**OpenWrt Syslog Viewer** is a lightweight real-time Syslog monitor for OpenWrt routers.

### 🎯 Purpose
- Real-time UDP syslog listener on port 514 with instant display and filtering.
- Silent background operation in the Windows system tray (`Start in Tray`) on Windows boot.
- Tray balloon notifications triggered only on mission-critical keywords.
- Fully portable: settings are kept locally in `config.json`.

### ✨ Features
- **UDP Syslog (port 514):** low-overhead ingestion of RFC 3164 / ISO 8601 streams.
- **Level Badges:** `EMERG`, `ALERT`, `CRIT`, `ERR`, `WARN`, `NOTE`, `INFO`, `DBUG`.
- **Keyword Highlighting:** highlights `error`, `failed`, `failure`, `timeout`, `refused`, `denied`, `warning`, and ANSI escape codes.
- **OpenWrt-Specific Heuristics:**
  - Reclassifies routine `crond` command executions to `INFO` (eliminating false `ERR`).
  - Cleans up false `ERR` from Go-based daemons (`torrserver`, `sing-box`).
  - Full support for `tachyon`: kernel kmsg redirect, submodule/level extraction, dedicated highlight color.
  - Strips redundant inner timestamps (AdGuardHome, Go loggers).
  - Elevates network disconnects (`link is down`) to `WARN`.
- **Filtering:** include/exclude by process (`Proc`) and message body (`Msg`), one-click process filter on table click.
- **Tray Alerts:** configurable keyword triggers with rate limiting.
- **Export & Clipboard:** Copy All button, **Ctrl+C** row copying, text file export with timestamps and log levels (`LVL`).
- **Dark UI:** VS Code-like dark theme with Windows 10/11 dark titlebar support.

### 📦 Installation & Quick Start (Windows)
1. **Download application:** **[openwrt-syslog-viewer (ZIP)](https://github.com/beermix/OpenWrt-Syslog-Viewer/archive/refs/heads/master.zip)** and extract anywhere.
2. **One-Click:** run **`install.bat`** (installs `PyQt6`, creates desktop shortcut, optionally configures autostart).
3. **Manual:**
   ```cmd
   pip install PyQt6
   run_openwrt_syslog_viewer.bat
   ```

### 🚀 Auto-start on Windows Boot
1. Check **`Auto-start`** in the application window (or choose `Y` during `install.bat`). It automatically manages the Windows Startup shortcut for `run_openwrt_syslog_viewer.bat`.
2. Check **`Start in Tray`** to silently start minimized to the system tray on Windows boot.

### ⚙️ OpenWrt Configuration
> [!IMPORTANT]
> **Required for operation:** For the viewer to capture and display logs, you must configure your OpenWrt router to send syslog messages to your PC's IP address.

* **Via LuCI:** **System** → **System** → **Logging** tab → enter your PC's IP, port `514`, protocol `UDP`.
* **Via SSH:**
  ```sh
  uci set system.@system[0].log_ip='<YOUR_PC_IP>'
  uci set system.@system[0].log_port='514'
  uci set system.@system[0].log_proto='udp'
  uci commit system && /etc/init.d/log restart
  ```

---

### 📄 License
MIT License.

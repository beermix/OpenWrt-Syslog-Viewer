# OpenWrt Syslog Viewer

<p align="center">
  <img src="pythonw_8KXqwNvxrU.png" alt="OpenWrt Syslog Viewer Screenshot" width="850">
</p>

<p align="center">
  <a href="#русский">Русский</a> •
  <a href="#english">English</a>
</p>

---

<a name="русский"></a>
## 🇷🇺 Русский

**OpenWrt Syslog Viewer** — легковесный, быстрый и удобный графический монитор системных логов (Syslog) для роутеров под управлением OpenWrt в реальном времени.

### 🎯 Цель проекта
Главная цель проекта — предоставить простую, отзывчивую и автономную утилиту, которая:
- **Отображает логи OpenWrt в реальном времени** с удобной подсветкой и фильтрацией.
- **Запускается при загрузке Windows свёрнутой в системный трей** (`Start in Tray`), тихо работает в фоновом режиме, не загромождает панель задач и мгновенно оповещает только при возникновении критических событий.
- **Полностью портативна:** файл настроек `config.json` хранится непосредственно в папке со скриптом, сохраняя фильтры, список алертов, состояние чекбоксов и размеры окна.

---

### ✨ Основные возможности

- 🚀 **Приём логов в реальном времени:** фоновый приём UDP-пакетов (порт 514) с высокой пропускной способностью и минимальной нагрузкой на процессор.
- 🎨 **Цветовые бейджи уровней важности:** наглядное визуальное разделение уровней `EMERG`, `ALERT`, `CRIT`, `ERR`, `WARN`, `NOTE`, `INFO`, `DBUG`.
- 🔍 **Умная подсветка синтаксиса:** автоматическое выделение цветом ключевых слов (`error`, `failed`, `warning`, `timeout`), а также полная поддержка ANSI escape-кодов терминала.
- ⚡ **Быстрый фильтр в один клик:** кликните по названию процесса в таблице, чтобы мгновенно отфильтровать вывод только по нему.
- 🛡️ **Гибкая фильтрация (включение / исключение):**
  - Раздельные поля для процессов (Proc) и текста сообщений (Msg) с перечислением через запятую.
  - Чекбоксы `!` для инвертирования (исключения) указанных процессов или нежелательных строк.
  - Кнопка полного отключения/включения фильтров (`Filters: ON/OFF`).
- 🔔 **Уведомления в трее (Alerts):** отслеживание критических событий (например, `SIGHUP`, `panic`, `attack`, `down`) со всплывающими сообщениями в трее Windows и встроенной защитой от флуда (throttling).
- 📌 **Интеграция с Windows Tray:** сворачивание в трей при закрытии окна, восстановление по клику и режим запуска в свёрнутом виде (`Start in Tray`).
- 💾 **Логирование на диск с авторотацией:** запись логов в файл `openwrt_logs.txt` с контролем размера (автоматическая ротация при достижении 100 МБ).
- 📋 **Экспорт и копирование:**
  - Кнопка **Copy All** для копирования всех отображаемых строк в буфер обмена.
  - Стандартное сочетание клавиш **Ctrl+C** и контекстное меню для копирования выделенных строк.
  - Экспорт в текстовый файл с сохранением временных меток и уровней важности (`LVL`).
- 🌙 **Современный Dark UI:** тёмный интерфейс с поддержкой нативной тёмной рамки окна Windows 10/11.

---

### 📦 Установка на Windows

#### Вариант 1. Автоматическая установка (в 1 клик)
1. Скачайте или клонируйте репозиторий:
   ```cmd
   git clone https://github.com/beermix/openwrt-syslog-viewer.git
   cd openwrt-syslog-viewer
   ```
2. Запустите файл **`install.bat`**.
   * Скрипт проверит наличие Python (версии 3.8+).
   * Автоматически установит библиотеку `PyQt6` из `requirements.txt`.
   * Создаст ярлык **OpenWrt Syslog Viewer** на вашем Рабочем столе для бесшумного запуска через `pythonw.exe` (без чёрного окна консоли).

#### Вариант 2. Ручная установка
```cmd
pip install -r requirements.txt
pythonw "openwrt syslog viewer.pyw"
```

> **Совет:** Для быстрого ручного запуска без открытия консоли также доступен файл **`run.bat`**.

---

### 🚀 Настройка автозапуска при загрузке Windows

Чтобы утилита автоматически стартовала вместе с операционной системой и сразу скрывалась в трей:

1. В верхней панели программы отметьте галочку **`Start in Tray`** (Запуск в трее).
2. Нажмите сочетание клавиш **`Win + R`**, введите:
   ```cmd
   shell:startup
   ```
   и нажмите **Enter** (откроется системная папка автозагрузки Windows).
3. Скопируйте созданный на Рабочем столе ярлык **OpenWrt Syslog Viewer** (или файл `run.bat`) в эту папку.

Теперь при включении компьютера утилита будет незаметно запускаться в системном трее и вести непрерывный приём логов.

---

### ⚙️ Настройка отправки логов в OpenWrt

Чтобы роутер отправлял системные сообщения на ваш компьютер:

#### Способ 1. Через веб-интерфейс LuCI
1. Перейдите в: **Система (System)** → **Система (System)** → вкладка **Журнал (Logging)**.
2. Заполните поля:
   - **IP-адрес внешнего сервера системного журнала (External system log server):** `<IP-адрес вашего компьютера>` (например, `192.168.1.100`)
   - **Порт внешнего сервера системного журнала (External system log server port):** `514`
   - **Протокол внешнего сервера системного журнала (External system log server protocol):** `UDP`
3. Нажмите **Сохранить и применить (Save & Apply)**.

#### Способ 2. Через консоль роутера (SSH)
Подключитесь к роутеру по SSH и выполните команды (замените `192.168.1.100` на локальный IP-адрес вашего ПК):
```sh
uci set system.@system[0].log_ip='192.168.1.100'
uci set system.@system[0].log_port='514'
uci set system.@system[0].log_proto='udp'
uci commit system
/etc/init.d/log restart
```

> **Примечание по Брандмауэру Windows:**  
> При первом запуске брандмауэр Windows может запросить разрешение на приём трафика. Разрешите приём пакетов для UDP-порта 514 в вашей частной сети.

---

### 📁 Хранение настроек (`config.json`)
Конфигурационный файл `config.json` хранится в одной папке с исполняемым скриптом. Это обеспечивает переносимость приложения (portable mode): при перемещении каталога программы все ваши сохранённые фильтры, история позиционирования окна и ключевые слова алертов останутся на месте.

---

<a name="english"></a>
## 🇬🇧 English

**OpenWrt Syslog Viewer** is a lightweight, fast, and responsive real-time Syslog monitoring tool designed for routers running OpenWrt.

### 🎯 Project Goal
The primary objective of this project is to provide a clean, standalone, and resilient utility that:
- **Monitors OpenWrt logs in real time** with intelligent syntax highlighting and rich filtering.
- **Starts automatically with Windows minimized to the system tray** (`Start in Tray`), silently listening for network events without cluttering the desktop or taskbar, and alerting the user only when critical events occur.
- **Is fully portable:** the `config.json` configuration file is stored directly within the script directory, keeping all filter rules, alert keywords, window geometry, and preferences completely self-contained.

---

### ✨ Features

- 🚀 **Real-time Syslog Stream:** High-performance background UDP receiver on port 514 with minimal system overhead.
- 🎨 **Level Badges:** Distinct, color-coded badges for `EMERG`, `ALERT`, `CRIT`, `ERR`, `WARN`, `NOTE`, `INFO`, `DBUG`.
- 🔍 **Syntax Highlighting:** Automatic color highlighting for `error`, `failed`, `warning`, `timeout` keywords and full ANSI terminal escape sequence rendering.
- ⚡ **One-Click Quick Filter:** Click any process name in the table to instantly filter logs by that specific process.
- 🛡️ **Flexible Include/Exclude Filtering:**
  - Dedicated inputs for processes (Proc) and message contents (Msg) using comma-separated values.
  - Inversion checkboxes `!` to exclude specific noise or background daemons.
  - Master toggle switch (`Filters: ON/OFF`).
- 🔔 **Keyword Tray Alerts:** Monitor mission-critical events (e.g. `SIGHUP`, `panic`, `attack`, `down`) with Windows Tray balloon notifications and flood throttling.
- 📌 **System Tray Integration:** Minimize to tray on close, restore on click, and seamless `Start in Tray` mode.
- 💾 **Disk Logging & Rotation:** Automatically writes incoming logs to `openwrt_logs.txt` with size-based rotation (100 MB ceiling).
- 📋 **Export & Clipboard:**
  - **Copy All** button to copy all visible log rows.
  - Standard **Ctrl+C** keyboard shortcut and right-click context menu for selected rows.
  - Text file export preserving timestamps and log levels (`LVL`).
- 🌙 **Modern Dark Theme:** Clean VS Code-inspired dark UI with native dark titlebar support on Windows 10/11.

---

### 📦 Windows Installation

#### Option 1. One-Click Auto-Installer
1. Clone or download the repository:
   ```cmd
   git clone https://github.com/beermix/openwrt-syslog-viewer.git
   cd openwrt-syslog-viewer
   ```
2. Double-click **`install.bat`**.
   * Checks for an existing Python installation (3.8+).
   * Installs required dependencies (`PyQt6`).
   * Generates an **OpenWrt Syslog Viewer** desktop shortcut (running silently via `pythonw.exe`).

#### Option 2. Manual Installation
```cmd
pip install -r requirements.txt
pythonw "openwrt syslog viewer.pyw"
```

> **Tip:** You can also launch the application anytime without a console window using **`run.bat`**.

---

### 🚀 Auto-start with Windows

To have the utility start automatically in the background when Windows boots:

1. In the application toolbar, check **`Start in Tray`**.
2. Press **`Win + R`**, type:
   ```cmd
   shell:startup
   ```
   and press **Enter** (opens the Windows Startup folder).
3. Copy the **OpenWrt Syslog Viewer** desktop shortcut (or `run.bat`) into this folder.

Now, upon Windows logon, the application will silently launch minimized into the system tray.

---

### ⚙️ OpenWrt Configuration

To stream syslog events from your router to your computer:

#### Via LuCI Web Interface
1. Navigate to: **System** → **System** → **Logging** tab.
2. Configure:
   - **External system log server:** `<Your PC IP Address>` (e.g. `192.168.1.100`)
   - **External system log server port:** `514`
   - **External system log server protocol:** `UDP`
3. Click **Save & Apply**.

#### Via SSH Terminal
Connect to your router via SSH and run (replace `192.168.1.100` with your PC's LAN IP):
```sh
uci set system.@system[0].log_ip='192.168.1.100'
uci set system.@system[0].log_port='514'
uci set system.@system[0].log_proto='udp'
uci commit system
/etc/init.d/log restart
```

---

### 📁 Configuration Storage (`config.json`)
All application settings (filters, alert keywords, window dimensions, and flags) are saved in `config.json` inside the program's folder. This makes the application completely portable.

---

### 📄 License

MIT License. Free for personal and commercial use.

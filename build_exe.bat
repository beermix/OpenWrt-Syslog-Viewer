@echo off
chcp 65001 >nul
title Сборка OpenWrt-Syslog-Viewer.exe
cd /d "%~dp0"

echo ===================================================
echo   Сборка OpenWrt-Syslog-Viewer.exe (PyInstaller)
echo ===================================================
echo.

:: 1. Проверка Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ОШИБКА] Python не найден в системе!
    pause
    exit /b 1
)

:: 2. Проверка и установка зависимостей сборки
echo [1/4] Проверка необходимых пакетов (PyQt6, PyInstaller, Pillow)...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install PyQt6 pyinstaller pillow
if %errorlevel% neq 0 (
    echo [ОШИБКА] Не удалось установить зависимости для сборки!
    pause
    exit /b 1
)

:: 3. Генерация иконки app_icon.ico
echo [2/4] Генерация app_icon.ico...
if not exist "app_icon.ico" (
    python generate_icon.py
)

:: 4. Сборка через PyInstaller
echo [3/4] Сборка исполняемого файла через PyInstaller...
set "ICON_PARAM="
if exist "app_icon.ico" (
    set "ICON_PARAM=--icon=app_icon.ico"
)

python -m PyInstaller ^
    --name="OpenWrt-Syslog-Viewer" ^
    --onefile ^
    --noconsole ^
    --clean ^
    %ICON_PARAM% ^
    "openwrt syslog viewer.py"

if %errorlevel% neq 0 (
    echo.
    echo [ОШИБКА] Сборка PyInstaller завершилась с ошибкой!
    pause
    exit /b 1
)

:: 5. Копирование готового файла в корень
echo [4/4] Копирование OpenWrt-Syslog-Viewer.exe...
if exist "dist\OpenWrt-Syslog-Viewer.exe" (
    copy /y "dist\OpenWrt-Syslog-Viewer.exe" "OpenWrt-Syslog-Viewer.exe" >nul
)

echo.
echo ===================================================
echo   Сборка успешно завершена!
echo   Создан файл: OpenWrt-Syslog-Viewer.exe
echo ===================================================
echo.
pause
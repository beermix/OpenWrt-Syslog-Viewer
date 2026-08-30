@echo off
chcp 65001 >nul
title Установка OpenWrt Syslog Viewer

cd /d "%~dp0"

echo ===================================================
echo     Установка OpenWrt Syslog Viewer (Windows)
echo ===================================================
echo.

:: 1. Проверка наличия Python
echo [1/3] Проверка наличия Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ОШИБКА] Python не найден в системе!
    echo Пожалуйста, установите Python версии 3.8 или новее с официального сайта:
    echo https://www.python.org/downloads/
    echo.
    echo [ВАЖНО] При установке обязательно включите опцию:
    echo "[x] Add Python to PATH" (Добавить Python в переменные среды).
    echo.
    echo ---------------------------------------------------
    echo [ERROR] Python is not installed or not in PATH!
    echo Please download and install Python from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during setup.
    echo ---------------------------------------------------
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set "PY_VER=%%i"
echo Обнаружен: %PY_VER%
echo.

:: 2. Установка зависимостей
echo [2/3] Установка необходимых библиотек (PyQt6)...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [ОШИБКА] Не удалось установить зависимости через pip!
    echo Проверьте подключение к интернету и повторите попытку.
    echo.
    pause
    exit /b 1
)
echo Зависимости успешно установлены.
echo.

:: 3. Создание ярлыка на Рабочем столе
echo [3/3] Создание ярлыка на Рабочем столе...
set "SCRIPT_DIR=%~dp0"
set "APP_PATH=%SCRIPT_DIR%openwrt syslog viewer.pyw"

where pythonw.exe >nul 2>&1
if %errorlevel% equ 0 (
    for /f "delims=" %%i in ('where pythonw.exe 2^>nul') do set "PYTHONW_EXE=%%i"
) else (
    set "PYTHONW_EXE=pythonw.exe"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell; " ^
  "$desktopPath = [Environment]::GetFolderPath('Desktop'); " ^
  "$shortcutPath = [IO.Path]::Combine($desktopPath, 'OpenWrt Syslog Viewer.lnk'); " ^
  "$s = $ws.CreateShortcut($shortcutPath); " ^
  "$s.TargetPath = '%PYTHONW_EXE%'; " ^
  "$s.Arguments = '\"%APP_PATH%\"'; " ^
  "$s.WorkingDirectory = '%SCRIPT_DIR%'; " ^
  "$s.Description = 'OpenWrt Syslog Viewer'; " ^
  "$s.Save(); " ^
  "if (Test-Path $shortcutPath) { Write-Host 'Ярлык \"OpenWrt Syslog Viewer\" успешно создан на Рабочем столе.' } else { Write-Host 'Ярлык можно запускать через файл: run.bat' }"

echo.
set "ADD_STARTUP=n"
set /p "ADD_STARTUP=Добавить запуск программы при загрузке Windows? [Y/N, по умолчанию N]: "
if /i "%ADD_STARTUP%"=="y" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "$ws = New-Object -ComObject WScript.Shell; " ^
      "$startupPath = [IO.Path]::Combine([Environment]::GetFolderPath('Startup'), 'OpenWrt Syslog Viewer.lnk'); " ^
      "$s = $ws.CreateShortcut($startupPath); " ^
      "$s.TargetPath = '%PYTHONW_EXE%'; " ^
      "$s.Arguments = '\"%APP_PATH%\"'; " ^
      "$s.WorkingDirectory = '%SCRIPT_DIR%'; " ^
      "$s.Description = 'OpenWrt Syslog Viewer'; " ^
      "$s.Save(); " ^
      "if (Test-Path $startupPath) { Write-Host 'Программа успешно добавлена в автозагрузку Windows (Startup).' }"
)

echo.
echo ===================================================
echo     Установка успешно завершена!
echo ===================================================
echo.
echo Для запуска используйте ярлык на Рабочем столе
echo или файл run.bat в этой папке.
echo.
pause

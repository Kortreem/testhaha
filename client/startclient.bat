@echo off
title Driver Client - Portable
echo ========================================
echo    DRIVER CLIENT - PORTABLE VERSION
echo ========================================
echo.

set PYTHON_PATH=python_portable\python.exe
set PIP_PATH=python_portable\Scripts\pip.exe

if not exist "%PYTHON_PATH%" (
    echo [ERROR] Портативный Python не найден!
    echo.
    echo Скачайте с: 
    echo https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip
    echo и распакуйте в папку python_portable
    pause
    exit /b 1
)

echo [OK] Используем портативный Python
echo.

echo [INFO] Устанавливаем зависимости...
"%PYTHON_PATH%" -m pip install -r requirements.txt

echo.
echo [INFO] Запускаем клиент...
echo [INFO] Сервер: http://localhost:8000
echo.

"%PYTHON_PATH%" client.py http://localhost:8000

echo.
echo ========================================
echo    Клиент завершил работу
echo ========================================
pause
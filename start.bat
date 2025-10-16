@echo off
echo Запуск бэкенда...
start cmd /k "python run.py"
timeout /t 3
echo Открываю фронтенд...
start frontend\index.html
echo Готово!
@echo off
echo Downloading Portable Python...
echo.

powershell -Command "& {
    Invoke-WebRequest -Uri 'https://github.com/indygreg/python-build-standalone/releases/download/20231002/cpython-3.11.5+20231002-x86_64-pc-windows-msvc-shared-install_only.tar.gz' -OutFile 'python-portable.tar.gz'
    tar -xzf python-portable.tar.gz
    move python-3.11.5-windows-x86_64 python
    del python-portable.tar.gz
    echo Portable Python ready!
}"
pause
@echo off
chcp 65001 >nul
cd /d "C:\Users\Lenovo\PycharmProjects\Djangolearn"

set STATIC_SOURCE=C:\Users\Lenovo\PycharmProjects\Djangolearn\static
set STATIC_TARGET=C:\Users\Lenovo\PycharmProjects\Djangolearn\static_collect
set FLAG_FILE=%STATIC_TARGET%\.last_collect

if not exist "%STATIC_TARGET%" mkdir "%STATIC_TARGET%"

for /f %%i in ('powershell -Command "(Get-ChildItem -Path "%STATIC_SOURCE%" -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime.Ticks"') do set SRC_TICKS=%%i

set NEED_COLLECT=1
if exist "%FLAG_FILE%" (
    set /p LAST_TICKS=<"%FLAG_FILE%"
    if "%SRC_TICKS%"=="%LAST_TICKS%" set NEED_COLLECT=0
)

if %NEED_COLLECT% == 1 (
    echo Static files updated → running collectstatic...
    py -3.14 manage.py collectstatic --noinput
    echo %SRC_TICKS% > "%FLAG_FILE%"
) else (
    echo No static changes → skip collectstatic.
)


py -3.14 -m waitress --threads=8 --listen=127.0.0.1:5000 Djangolearn.wsgi:application
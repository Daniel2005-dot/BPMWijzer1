@echo off
setlocal
cd /d "%~dp0"
set "PYTHON="
where py >nul 2>nul
if not errorlevel 1 (
  py -3 --version >nul 2>nul
  if not errorlevel 1 set "PYTHON=py -3"
)
if not defined PYTHON (
  where python >nul 2>nul
  if not errorlevel 1 (
    python --version >nul 2>nul
    if not errorlevel 1 set "PYTHON=python"
  )
)
if not defined PYTHON (
  echo Python 3 is niet geinstalleerd of Windows verwijst alleen naar de Microsoft Store-snelkoppeling.
  echo Installeer Python 3 via: https://www.python.org/downloads/windows/
  echo Kies tijdens de installatie voor "Add python.exe to PATH".
  echo Start daarna start_windows.bat opnieuw.
  pause
  exit /b 1
)
%PYTHON% -c "import dateutil" >nul 2>nul
if errorlevel 1 (
  echo Benodigde Python-module wordt geinstalleerd...
  %PYTHON% -m pip --version >nul 2>nul
  if errorlevel 1 (
    echo Python is gevonden, maar pip ontbreekt. Herstel of installeer Python opnieuw.
    pause
    exit /b 1
  )
  %PYTHON% -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Installeren van de Python-module is mislukt. Controleer je internetverbinding en probeer opnieuw.
    pause
    exit /b 1
  )
)
%PYTHON% server.py
pause

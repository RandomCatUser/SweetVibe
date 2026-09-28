@echo off
echo Building the executable with PyInstaller...

powershell -NoProfile -Command "if (Get-Process -Name SweetVibe -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }"
if %ERRORLEVEL% neq 0 (
    echo.
    echo SweetVibe is currently running. Close all SweetVibe windows before building.
    pause
    exit /b 1
)

REM Run PyInstaller using the existing configuration
pyinstaller main.spec --noconfirm --clean

if %ERRORLEVEL% neq 0 (
    echo PyInstaller failed.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo PyInstaller finished successfully.
echo.
echo Building the Inno Setup installer...

REM Locate ISCC.exe: machine-wide installs, then per-user installs (winget
REM puts Inno Setup in %LOCALAPPDATA%\Programs), then PATH.
REM Set ISCC_PATH="C:\path\to\ISCC.exe" beforehand to force a specific one.
if not defined ISCC_PATH (
    for %%P in (
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
        "C:\Program Files\Inno Setup 6\ISCC.exe"
        "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
        "C:\Program Files (x86)\Inno Setup 7\ISCC.exe"
        "C:\Program Files\Inno Setup 7\ISCC.exe"
        "%LOCALAPPDATA%\Programs\Inno Setup 7\ISCC.exe"
    ) do (
        if not defined ISCC_PATH if exist %%P set ISCC_PATH=%%P
    )
)

if not defined ISCC_PATH (
    for /f "delims=" %%I in ('where iscc 2^>nul') do (
        if not defined ISCC_PATH set ISCC_PATH="%%~fI"
    )
)

if not defined ISCC_PATH (
    echo ERROR: Inno Setup compiler ^(ISCC.exe^) was not found.
    echo        Install Inno Setup 6 ^(https://jrsoftware.org/isinfo.php^)
    echo        or set  ISCC_PATH="C:\path\to\ISCC.exe"  before building.
    pause
    exit /b 1
)

echo Using %ISCC_PATH%
%ISCC_PATH% setup.iss

if %ERRORLEVEL% neq 0 (
    echo Inno Setup compilation failed.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Build complete! Your installer is located in dist\installer
pause

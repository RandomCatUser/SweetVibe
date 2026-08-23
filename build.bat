@echo off
echo Building the executable with PyInstaller...

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

set ISCC_PATH="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %ISCC_PATH% (
    set ISCC_PATH="C:\Program Files\Inno Setup 6\ISCC.exe"
)

if exist %ISCC_PATH% (
    %ISCC_PATH% setup.iss
) else (
    echo Warning: Could not find Inno Setup compiler in standard paths. Trying PATH...
    iscc setup.iss
)

if %ERRORLEVEL% neq 0 (
    echo Inno Setup compilation failed.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Build complete! Your installer is located in dist\installer
pause

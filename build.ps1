# Build Script for SweetVibe
# Run this script whenever you update the code to easily generate the executable and installer.

Write-Host "Building the executable with PyInstaller..." -ForegroundColor Cyan

# Run PyInstaller using the existing configuration
# Note: main.spec already specifies ico.ico as the icon and sets up the correct build folder (dist\SweetVibe).
pyinstaller main.spec --noconfirm --clean

if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller failed. Please check the output above." -ForegroundColor Red
    exit 1
}

Write-Host "`nPyInstaller finished successfully." -ForegroundColor Green
Write-Host "`nBuilding the Inno Setup installer..." -ForegroundColor Cyan

# Find the Inno Setup compiler (iscc.exe)
# Usually installed in standard Program Files paths
$iscc_path = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

if (-Not (Test-Path $iscc_path)) {
    # If not in x86, check standard Program Files
    $iscc_path = "C:\Program Files\Inno Setup 6\ISCC.exe"
}

if (-Not (Test-Path $iscc_path)) {
    Write-Host "Warning: Could not find Inno Setup compiler (ISCC.exe) in standard paths." -ForegroundColor Yellow
    Write-Host "If you have Inno Setup installed elsewhere or added to your PATH, please compile setup.iss manually or update this script with the correct path."
    
    # Try running it from PATH just in case
    try {
        iscc setup.iss
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Inno Setup compilation failed." -ForegroundColor Red
            exit 1
        }
    }
    catch {
        Write-Host "Inno Setup compiler not found in PATH." -ForegroundColor Red
    }
}
else {
    & $iscc_path setup.iss
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Inno Setup compilation failed. Please check the output above." -ForegroundColor Red
        exit 1
    }
}

Write-Host "`nBuild complete! Your installer is located in dist\installer" -ForegroundColor Green

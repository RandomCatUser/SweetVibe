# Build Script for SweetVibe
# Run this script whenever you update the code to easily generate the executable and installer.

Write-Host "Building the executable with PyInstaller..." -ForegroundColor Cyan

$running_app = Get-Process -Name SweetVibe -ErrorAction SilentlyContinue
if ($running_app) {
    Write-Host "SweetVibe is currently running. Close all SweetVibe windows before building." -ForegroundColor Red
    exit 1
}

# Run PyInstaller using the existing configuration
# Note: main.spec already specifies ico.ico as the icon and sets up the correct build folder (dist\SweetVibe).
pyinstaller main.spec --noconfirm --clean

if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller failed. Please check the output above." -ForegroundColor Red
    exit 1
}

Write-Host "`nPyInstaller finished successfully." -ForegroundColor Green
Write-Host "`nBuilding the Inno Setup installer..." -ForegroundColor Cyan

# Find the Inno Setup compiler (ISCC.exe):
#   1. $env:ISCC_PATH, if you set one to force a specific compiler
#   2. machine-wide installs (Program Files / Program Files (x86))
#   3. per-user installs - winget puts Inno Setup in %LOCALAPPDATA%\Programs
#   4. the uninstall registry (any location)
#   5. PATH
$iscc_path = $env:ISCC_PATH
if ($iscc_path -and -Not (Test-Path $iscc_path)) { $iscc_path = $null }

if (-Not $iscc_path) {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 7\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 7\ISCC.exe"
    )
    $iscc_path = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}

if (-Not $iscc_path) {
    $uninstRoots = @(
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall',
        'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'
    )
    foreach ($root in $uninstRoots) {
        $entry = Get-ItemProperty "$root\*" -ErrorAction SilentlyContinue |
                 Where-Object { $_.DisplayName -like 'Inno Setup*' -and $_.InstallLocation } |
                 Sort-Object DisplayName -Descending | Select-Object -First 1
        if ($entry) {
            $probe = Join-Path $entry.InstallLocation 'ISCC.exe'
            if (Test-Path $probe) { $iscc_path = $probe; break }
        }
    }
}

if (-Not $iscc_path) {
    $cmd = Get-Command iscc -ErrorAction SilentlyContinue
    if ($cmd) { $iscc_path = $cmd.Source }
}

if (-Not $iscc_path) {
    Write-Host "ERROR: Inno Setup compiler (ISCC.exe) was not found." -ForegroundColor Red
    Write-Host "       Install Inno Setup 6 (https://jrsoftware.org/isinfo.php) or" -ForegroundColor Red
    Write-Host '       set  $env:ISCC_PATH="C:\path\to\ISCC.exe"  before building.' -ForegroundColor Red
    exit 1
}

Write-Host "Using $iscc_path" -ForegroundColor DarkGray
& $iscc_path setup.iss
if ($LASTEXITCODE -ne 0) {
    Write-Host "Inno Setup compilation failed. Please check the output above." -ForegroundColor Red
    exit 1
}

Write-Host "`nBuild complete! Your installer is located in dist\installer" -ForegroundColor Green

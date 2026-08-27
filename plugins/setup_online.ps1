$ErrorActionPreference = 'Stop'

$python = (Get-Command py -ErrorAction SilentlyContinue).Source
if (-not $python) {
    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
}

if (-not $python) {
    $url = 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe'
    $installer = Join-Path $env:TEMP 'SweetVibePython.exe'
    Write-Host 'Python was not found. Downloading Python 3.12...'
    Invoke-WebRequest -Uri $url -OutFile $installer
    Start-Process $installer -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1 Include_test=0' -Wait
    Remove-Item $installer -Force
    $python = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
}

if (-not (Test-Path $python)) {
    throw 'Python could not be installed or located.'
}

& $python (Join-Path $PSScriptRoot 'setup_yt_dlp.py')
exit $LASTEXITCODE

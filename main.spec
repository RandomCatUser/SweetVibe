# -*- mode: python ; coding: utf-8 -*-
import shutil

from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = ['win32con', 'win32api', 'pywintypes']
for package in ('asciimatics', 'tinytag', 'just_playback'):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports
yt_dlp_exe = shutil.which('yt-dlp')
if not yt_dlp_exe:
    raise SystemExit('yt-dlp.exe is required to build SweetVibe. Install it with: python -m pip install --upgrade yt-dlp')
binaries.append((yt_dlp_exe, '.'))
datas.append(('songs', 'songs'))
datas.append(('plugins', 'plugins'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ['_cffi_backend'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    [],
    name='SweetVibe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['ico.ico'],
    version='version_info.txt',
    contents_directory='.',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SweetVibe',
)

# Building an Executable & Installer

SweetVibe ships as a single portable executable bundled by PyInstaller, wrapped
into an installer by Inno Setup. This guide explains the build prerequisites,
the two-step build, and how to avoid antivirus false positives when sharing the
EXE.

---

## Prerequisites

- **Python** with the project dependencies installed
  (`asciimatics`, `tinytag`, `just_playback`; optionally `numpy` + `soundfile`).
- **PyInstaller** available on your PATH as `pyinstaller`.
- **Inno Setup 6** installed so `ISCC.exe` is available.
- **yt-dlp** installed via pip (the build collects the Python package).

Install the Python build tooling:

```bash
python -m pip install asciimatics tinytag just_playback numpy soundfile pyinstaller
python -m pip install --upgrade yt-dlp
```

---

## The two build steps

The release build produces:

1. A **portable application** in `dist\SweetVibe\` (built by PyInstaller).
2. An **installer** at `dist\installer\Setup_Windows_x64.exe`
   (built by Inno Setup).

Both steps are driven by the configuration in:

- `main.spec` - PyInstaller configuration.
- `setup.iss` - Inno Setup installer script.

### Build with the provided scripts

From the project folder, run either:

```bat
build.bat
```

or:

```powershell
.\build.ps1
```

Both scripts:

1. Check that SweetVibe is not currently running.
2. Run `pyinstaller main.spec --noconfirm --clean`.
3. Compile the installer with Inno Setup.

---

## What `main.spec` controls

`main.spec` tells PyInstaller what to bundle:

- The entry script (`main.py`).
- Python packages collected recursively for `asciimatics`, `tinytag`,
  `just_playback`, and `yt_dlp`.
- The `songs` folder and the `plugins` folder.
- The icon (`ico.ico`).
- Windows **version info** from `version_info.txt` (product name, company,
  description, version `1.4.2`).

### yt-dlp is bundled as a library, not an executable

The spec collects the `yt_dlp` Python package with `collect_all()` instead of
copying a standalone `yt-dlp.exe` next to the player. Consequences worth
knowing:

- **No `yt-dlp.exe` in the release.** There is no self-contained binary for
  antivirus/PUA heuristics to flag, which was the reason for this change.
- **No PATH lookup at runtime.** `plugins/online.py` does `import yt_dlp`, so
  there is no installed-vs-bundled resolution to get wrong.
- **No subprocess and no scraped output.** The plugin gets progress from
  `progress_hooks` and the written path from `YoutubeDL.prepare_filename()`.
- **yt-dlp keeps working normally.** It still needs its usual CA certificates
  and a JS runtime for full YouTube support, exactly as before.

If `yt_dlp` cannot be imported at build time, the spec aborts with a clear
message.

---

## Version info

The embedded metadata lives in `version_info.txt` and is referenced by
`main.spec`. To bump it, update:

- `CURRENT_VERSION` in `main.py`,
- `version_info.txt` (`filevers`, `prodvers`, `FileVersion`, `ProductVersion`,
  `LegalCopyright`),
- `MyAppVersion` in `setup.iss`.

Keep them in sync so the EXE properties and installer report the same version.

---

For how the rest of the source is organized, see
[docs/architecture.md](architecture.md).

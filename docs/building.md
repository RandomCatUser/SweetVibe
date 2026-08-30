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
- **yt-dlp** on your PATH or installed via pip (the build bundles it).

Install the Python build tooling:

```bash
python -m pip install asciimatics tinytag just_playback numpy soundfile pyinstaller
python -m pip install --user --upgrade yt-dlp
```

---

## The two build steps

The release build produces:

1. A **portable application** in `dist\SweetVibe\` (built by PyInstaller).
2. An **installer** at `dist\installer\Setup_Windows_x64_v<version>.exe`
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
- Python packages collected recursively for `asciimatics`, `tinytag`, and
  `just_playback`.
- The bundled `yt-dlp.exe`, the `songs` folder, and the `plugins` folder.
- The icon (`ico.ico`).
- Windows **version info** from `version_info.txt` (product name, company,
  description, version `1.4.1`).

If `yt-dlp` is missing at build time, the spec aborts with a clear message.

---

## Avoiding antivirus false positives

PyInstaller executables are sometimes flagged by antivirus as a Trojan. This is
a **false positive** - the program is not malicious. It happens because packed,
single-file executables look structurally similar to real malware.

The most important fixes are already applied to this project:

1. **UPX is disabled.** In `main.spec`, both the `EXE` and `COLLECT` stages use
   `upx=False`. UPX-pack-compressed executables are the single biggest trigger
   for heuristic Trojan detection. If you ever re-enable it, expect more flags.

2. **Real Windows version info is embedded.** `main.spec` sets
   `version='version_info.txt'`, so the EXE reports a genuine product name,
   company, description, and version. Legitimate-looking binaries are flagged
   far less often.

### If an antivirus still flags the EXE

- **Code-sign the executable** with an Authenticode certificate. A valid
  signature removes most heuristics. Services such as Azure Trusted Signing or
  any purchased code-signing cert work; you then sign
  `dist\SweetVibe\SweetVibe.exe` (with e.g. `signtool`).
- **Report a false positive** to the antivirus vendor (Windows Defender,
  etc.). Most have a web form; they will review and allowlist the binary.
- Double-check the EXE you built matches the current `main.spec` - older UPX
  builds still get flagged.

### Things that increase flags (avoid unless you know why)

- Turning `upx` back on.
- Building with no icon and no version info.
- Downloading the EXE via an "unrecognized publisher" URL without any
  reputation.

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

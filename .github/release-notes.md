# SweetVibe 1.5.1

### Fixed

- **Downloads now land in the folder you are browsing.** A pinned download
  target that points inside the OS temp directory (a leftover from tests or a
  wiped `%TEMP%`) is detected and cleared on launch instead of silently
  hijacking every download to a folder you never chose. `:cache dir` also
  refuses to pin a temp path in the first place.

### Added

- **"Play in SweetVibe" on audio files.** Right-clicking an `.mp3`, `.aac`,
  `.m4a`, `.wav`, `.flac`, `.ogg`, `.opus` or `.webm` file in Windows Explorer
  now opens that file's folder in SweetVibe and starts playing it. Launching
  `SweetVibe.exe <path>` from the command line works the same way. A directory
  context-menu entry already existed; it now works as intended too. The
  context menu uses `SystemFileAssociations`, so no default handler is
  stolen from any existing player.

Full changelog: https://github.com/RandomCatUser/SweetVibe/compare/1.5.0...1.5.1

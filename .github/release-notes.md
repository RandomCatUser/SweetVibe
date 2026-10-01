# SweetVibe 1.5.0

### Changed

- **yt-dlp is now imported as a Python library.** SweetVibe used to ship a
  standalone `yt-dlp.exe` next to the player and run it as a subprocess,
  scraping the progress percentage out of stdout. The release now bundles the
  `yt_dlp` package instead, so `dist\SweetVibe` contains exactly one
  executable: `SweetVibe.exe`. Nothing extra for antivirus to flag, no console
  window, no PATH lookup to get wrong.
- Progress comes from yt-dlp's progress hooks and the finished path from
  `prepare_filename()`, which is exact rather than a title glob.
- The installation no longer needs a separate setup step for yt-dlp.

### Fixed

- **A download no longer leaves two files behind.** A fetched track is remuxed to
  Ogg Opus in pure Python and the original WebM is deleted, so one download is
  one playable file (#2).
- All yt-dlp output is captured internally, so it can never corrupt the TUI.

### Added

- **In-app update flow.** A modal reports checking, ready, downloading, done and
  error states, and can launch the installer for you. Dismissed versions are
  remembered so they do not nag on every launch. Versions are now compared
  numerically, so `1.10` correctly sorts above `1.9`.

### Docs

- The documentation site was rebuilt: the hero plays the `:girl` ASCII
  animation in a terminal window, and the docs moved to their own page with a
  sidebar.

Full changelog: https://github.com/RandomCatUser/SweetVibe/compare/1.4.0...1.5.0

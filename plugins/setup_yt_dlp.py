"""Guided per-user installation of yt-dlp for SweetVibe."""

import subprocess
import sys


def main():
    print("SweetVibe online music setup")
    print("This installs yt-dlp for your Windows user account.")
    answer = input("Install or update yt-dlp now? [Y/n]: ").strip().lower()
    if answer and answer not in ("y", "yes"):
        print("Skipped. Online search will remain unavailable until yt-dlp is installed.")
        return 0

    command = [sys.executable, "-m", "pip", "install", "--user", "--upgrade", "yt-dlp"]
    print("\nInstalling yt-dlp...")
    result = subprocess.run(command)
    if result.returncode:
        print("\nInstallation failed. You can retry with:")
        print("  " + " ".join(command))
        return result.returncode
    print("\nyt-dlp is ready. Press Enter to finish.")
    input()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
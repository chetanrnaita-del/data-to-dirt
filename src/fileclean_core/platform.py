"""Cross-platform utilities for FileClean."""

from __future__ import annotations

import platform
from pathlib import Path


def get_os() -> str:
    """Return normalized OS name: 'macos', 'windows', or 'linux'."""
    system = platform.system()
    if system == "Darwin":
        return "macos"
    elif system == "Windows":
        return "windows"
    else:
        return "linux"


def get_system_dirs() -> list[Path]:
    """Return directories that should NEVER be scanned or modified.

    These are critical OS directories whose contents should not be touched.
    """
    system = get_os()
    if system == "macos":
        return [
            Path("/System"),
            Path("/usr"),
            Path("/bin"),
            Path("/sbin"),
            Path("/Library"),
            Path("/cores"),
            Path("/dev"),
            Path("/etc"),
            Path("/private/etc"),
            Path("/private/var/root"),
            Path("/private/var/db"),
            Path("/private/var/audit"),
            Path("/private/var/run"),
            Path("/private/var/vm"),
        ]
    elif system == "windows":
        return [
            Path("C:/Windows"),
            Path("C:/Program Files"),
            Path("C:/Program Files (x86)"),
            Path("C:/ProgramData"),
            Path("C:/Recovery"),
            Path("C:/$Recycle.Bin"),
        ]
    else:  # linux
        return [
            Path("/boot"),
            Path("/usr"),
            Path("/bin"),
            Path("/sbin"),
            Path("/lib"),
            Path("/lib64"),
            Path("/sys"),
            Path("/proc"),
            Path("/dev"),
            Path("/etc"),
            Path("/var"),
            Path("/run"),
            Path("/snap"),
        ]


def get_default_scan_dirs() -> list[Path]:
    """Return suggested scan directories for the current OS.

    These are common user directories where junk tends to accumulate.
    """
    home = Path.home()
    common = [
        home / "Downloads",
        home / "Desktop",
        home / "Documents",
    ]

    system = get_os()
    if system == "macos":
        common.extend([
            home / "Library" / "Caches",
            home / "Movies",
            home / "Pictures",
            home / "Music",
        ])
    elif system == "windows":
        common.extend([
            home / "AppData" / "Local" / "Temp",
            home / "Videos",
            home / "Pictures",
            home / "Music",
        ])
    else:  # linux
        common.extend([
            home / ".cache",
            home / "Videos",
            home / "Pictures",
            home / "Music",
        ])

    return [d for d in common if d.exists()]


def is_system_dir(path: Path) -> bool:
    """Check if a path is inside a protected system directory."""
    resolved = path.resolve()
    for sys_dir in get_system_dirs():
        try:
            resolved.relative_to(sys_dir.resolve())
            return True
        except ValueError:
            continue
    return False


def open_in_file_manager(path: Path) -> None:
    """Open a file or directory in the system's file manager."""
    import subprocess
    system = get_os()

    target = path if path.is_dir() else path.parent

    if system == "macos":
        if path.is_file():
            subprocess.Popen(["open", "-R", str(path)])
        else:
            subprocess.Popen(["open", str(target)])
    elif system == "windows":
        if path.is_file():
            subprocess.Popen(["explorer", "/select,", str(path)])
        else:
            subprocess.Popen(["explorer", str(target)])
    else:  # linux
        subprocess.Popen(["xdg-open", str(target)])

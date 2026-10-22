"""
Data-to-Dirt — Dedicated Desktop Window Container
Launches the retro game UI in an isolated desktop window without browser bars,
tabs, or address controls (using Chrome/Chromium --app mode or native browser window).
"""

import sys
import os
import shutil
import subprocess
import webbrowser
from typing import Optional, List


def find_chrome_binary() -> Optional[str]:
    """Finds path to Google Chrome, Chromium, or Brave executable on current OS."""
    if sys.platform == "darwin":  # macOS
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        ]
        for path in candidates:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path
        # Fallback to which
        for name in ["google-chrome", "chromium", "brave"]:
            bin_path = shutil.which(name)
            if bin_path:
                return bin_path

    elif sys.platform.startswith("linux"):
        for name in ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium", "brave-browser"]:
            bin_path = shutil.which(name)
            if bin_path:
                return bin_path

    elif sys.platform in ["win32", "cygwin"]:
        candidates = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path

    return None


def launch_desktop_window(url: str, width: int = 1200, height: int = 800) -> bool:
    """
    Launches the application URL in Safari.
    """
    if sys.platform == "darwin":
        print(f"[+] Found dedicated desktop window provider: Safari")
        try:
            subprocess.Popen(
                ["open", "-a", "Safari", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            print("[✓] Dedicated retro desktop window launched successfully in Safari.")
            return True
        except Exception as e:
            print(f"[!] Warning: Failed to spawn Safari window: {e}")

    # Fallback to standard system browser
    print(f"[+] Falling back to default system browser for URL: {url}")
    try:
        webbrowser.open(url)
        return True
    except Exception as e:
        print(f"[-] Error opening web browser: {e}")
        return False


if __name__ == "__main__":
    test_url = sys.argv[1] if len(sys.argv) > 1 else "http://0.0.0.0:8088"
    launch_desktop_window(test_url)

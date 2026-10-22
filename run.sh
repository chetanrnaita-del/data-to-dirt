#!/usr/bin/env bash
# ==============================================================================
# Data-to-Dirt — Single-Command Desktop Launcher
# Launches local backend HTTP service and opens dedicated retro game desktop window
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON="${PYTHON:-python3}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "[-] Error: python3 is not installed or not in PATH."
    exit 1
fi

echo "=================================================="
echo "  DATA-TO-DIRT: Retro Desktop Application Launch  "
echo "=================================================="
echo "[+] Working directory: $SCRIPT_DIR"
echo "[+] Starting server and opening game window..."

exec "$PYTHON" src/app/server.py --launch-window "$@"

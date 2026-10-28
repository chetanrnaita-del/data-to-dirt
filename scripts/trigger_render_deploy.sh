#!/usr/bin/env bash
# Data-to-Dirt — One-command Render Deployment Trigger
set -e

HOOK_URL="${1:-$RENDER_DEPLOY_HOOK}"

if [ -z "$HOOK_URL" ]; then
    echo "=================================================="
    echo "  Data-to-Dirt Render Auto-Deploy Utility         "
    echo "=================================================="
    echo "Usage: ./scripts/trigger_render_deploy.sh <DEPLOY_HOOK_URL>"
    echo "Or set RENDER_DEPLOY_HOOK in your environment."
    echo ""
    echo "To get your Deploy Hook URL:"
    echo "  1. Go to https://dashboard.render.com"
    echo "  2. Select 'data-to-dirt' -> Settings"
    echo "  3. Scroll down to 'Deploy Hook' and copy the URL"
    echo "=================================================="
    exit 1
fi

echo "[+] Triggering automatic deploy on Render..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$HOOK_URL")

if [ "$HTTP_STATUS" -eq 200 ] || [ "$HTTP_STATUS" -eq 201 ]; then
    echo "[✓] Successfully triggered Render deployment! (HTTP $HTTP_STATUS)"
    echo "[+] Render is building the latest commit from origin/main."
else
    echo "[!] Deployment trigger returned HTTP status: $HTTP_STATUS"
fi

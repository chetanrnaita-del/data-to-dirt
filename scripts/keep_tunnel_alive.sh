#!/bin/bash
# Auto-reconnecting tunnel daemon for datatodirt.loca.lt

echo "[+] Starting persistent tunnel monitor for https://datatodirt.loca.lt"

while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting localtunnel on port 8088 with subdomain datatodirt..."
    npx --yes localtunnel --port 8088 --subdomain datatodirt
    EXIT_CODE=$?
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] localtunnel exited with code $EXIT_CODE. Reconnecting in 3 seconds..."
    sleep 3
done

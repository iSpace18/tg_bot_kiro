#!/bin/bash

echo "=== Checking VPN Configuration ==="
echo ""

# Get latest UUID
echo "Latest created client UUID:"
docker logs vpn_telegram_bot 2>&1 | grep "Client.*created via API" | tail -1 | grep -oP 'UUID \K[a-f0-9-]+'

echo ""
echo "=== Reality Configuration ==="
sqlite3 /etc/x-ui/x-ui.db "SELECT json_extract(stream_settings, '$.realitySettings.dest') as dest, json_extract(stream_settings, '$.realitySettings.serverNames') as serverNames FROM inbounds WHERE protocol='vless';"

echo ""
echo "=== Checking if client exists in x-ui ==="
UUID=$(docker logs vpn_telegram_bot 2>&1 | grep "Client.*created via API" | tail -1 | grep -oP 'UUID \K[a-f0-9-]+')
sqlite3 /etc/x-ui/x-ui.db "SELECT settings FROM inbounds WHERE id=1;" | grep -q "$UUID" && echo "✅ Client found in x-ui" || echo "❌ Client NOT found in x-ui"

echo ""
echo "=== X-UI Service Status ==="
systemctl status x-ui | grep Active

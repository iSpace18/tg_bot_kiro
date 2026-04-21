#!/bin/bash

# Update Reality configuration to use djanvpn.ru domain

DOMAIN="djanvpn.ru"
XUI_DB="/etc/x-ui/x-ui.db"

echo "=========================================="
echo "Updating Reality configuration"
echo "New domain: $DOMAIN"
echo "=========================================="

# Backup current database
cp $XUI_DB ${XUI_DB}.backup_domain_$(date +%Y%m%d_%H%M%S)
echo "✅ Database backed up"

# Get current stream_settings
CURRENT_SETTINGS=$(sqlite3 $XUI_DB "SELECT stream_settings FROM inbounds WHERE protocol='vless' LIMIT 1;")

echo "Current settings:"
echo "$CURRENT_SETTINGS" | python3 -m json.tool

# Update with new domain using Python
python3 << 'PYTHON_SCRIPT'
import sqlite3
import json

DB_PATH = "/etc/x-ui/x-ui.db"
DOMAIN = "djanvpn.ru"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get current stream_settings
cursor.execute("SELECT stream_settings FROM inbounds WHERE protocol='vless' LIMIT 1")
row = cursor.fetchone()

if row:
    settings = json.loads(row[0])
    
    # Update Reality settings
    if 'realitySettings' in settings:
        settings['realitySettings']['dest'] = f'{DOMAIN}:443'
        settings['realitySettings']['serverNames'] = [DOMAIN, f'www.{DOMAIN}']
        
        # Update in database
        cursor.execute(
            "UPDATE inbounds SET stream_settings = ? WHERE protocol = 'vless'",
            (json.dumps(settings),)
        )
        conn.commit()
        print(f"✅ Updated Reality settings with domain: {DOMAIN}")
        print(f"   dest: {settings['realitySettings']['dest']}")
        print(f"   serverNames: {settings['realitySettings']['serverNames']}")
    else:
        print("❌ No realitySettings found")
else:
    print("❌ No VLESS inbound found")

conn.close()
PYTHON_SCRIPT

echo "✅ Reality configuration updated in database"

# Restart x-ui service
systemctl restart x-ui
echo "✅ x-ui service restarted"

echo ""
echo "=========================================="
echo "✅ Configuration update complete!"
echo "=========================================="

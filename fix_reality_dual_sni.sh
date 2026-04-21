#!/bin/bash

echo "=== Updating Reality to support dual SNI ==="

# Update Reality settings to support both google.com and djanvpn.ru
python3 << 'PYTHON_SCRIPT'
import sqlite3
import json

DB_PATH = "/etc/x-ui/x-ui.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get current stream_settings
cursor.execute("SELECT stream_settings FROM inbounds WHERE protocol='vless' LIMIT 1")
row = cursor.fetchone()

if row:
    settings = json.loads(row[0])
    
    # Update Reality settings to support both SNIs
    if 'realitySettings' in settings:
        # Keep djanvpn.ru as dest, but add google.com to serverNames
        settings['realitySettings']['serverNames'] = [
            "www.google.com",
            "google.com", 
            "djanvpn.ru",
            "www.djanvpn.ru"
        ]
        
        # Update in database
        cursor.execute(
            "UPDATE inbounds SET stream_settings = ? WHERE protocol = 'vless'",
            (json.dumps(settings),)
        )
        conn.commit()
        print("✅ Updated Reality settings to support both SNIs")
        print(f"   serverNames: {settings['realitySettings']['serverNames']}")
    else:
        print("❌ No realitySettings found")
else:
    print("❌ No VLESS inbound found")

conn.close()
PYTHON_SCRIPT

# Restart x-ui
systemctl restart x-ui
echo "✅ X-UI restarted"

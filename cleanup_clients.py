#!/usr/bin/env python3
import sqlite3
import json
import uuid
from datetime import datetime, timedelta

DB_PATH = "/etc/x-ui/x-ui.db"
ADMIN_TELEGRAM_ID = "1658346274"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get VLESS inbound
cursor.execute("SELECT id, settings, port FROM inbounds WHERE protocol='vless' LIMIT 1")
row = cursor.fetchone()
if not row:
    print("Error: VLESS inbound not found")
    exit(1)

inbound_id, settings_json, port = row
settings = json.loads(settings_json)

print(f"Current clients: {len(settings.get('clients', []))}")

# Create new trial client for admin
new_uuid = str(uuid.uuid4())
expiry_ts = int((datetime.utcnow() + timedelta(days=3)).timestamp() * 1000)

new_client = {
    "id": new_uuid,
    "email": f"trial_{ADMIN_TELEGRAM_ID}",
    "flow": "xtls-rprx-vision",
    "enable": True,
    "expiryTime": expiry_ts,
    "totalGB": 10737418240,  # 10 GB
    "limitIp": 1
}

# Replace all clients with just the new one
settings["clients"] = [new_client]

# Update database
cursor.execute("UPDATE inbounds SET settings=? WHERE id=?", (json.dumps(settings), inbound_id))
conn.commit()

print(f"\nCleanup complete!")
print(f"Removed all old clients")
print(f"Created new trial client:")
print(f"  Email: trial_{ADMIN_TELEGRAM_ID}")
print(f"  UUID: {new_uuid}")
print(f"  Expiry: {datetime.fromtimestamp(expiry_ts / 1000).strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  Traffic: 10 GB")
print(f"  Port: {port}")

# Generate VLESS URL
server_ip = "89.44.76.190"
display_name = "⚡ | 🇳🇱 Reality [VPN] Trial"
from urllib.parse import quote

vless_url = (
    f"vless://{new_uuid}@{server_ip}:{port}"
    f"?type=tcp&security=reality&pbk=c4d33NKVpulPMhdJOcq-e12fjJjRZMU5V_wTTIm5K2c"
    f"&fp=chrome&sni=www.google.com&sid=0123456789abcdef&spx=%2F"
    f"&flow=xtls-rprx-vision"
    f"#{quote(display_name)}"
)

print(f"\nVLESS URL:")
print(vless_url)

conn.close()

#!/usr/bin/env python3
import sqlite3
import json
from datetime import datetime
from urllib.parse import quote

XUI_DB_PATH = "/etc/x-ui/x-ui.db"
ADMIN_TELEGRAM_ID = 1658346274

conn = sqlite3.connect(XUI_DB_PATH)
cursor = conn.cursor()

# Get inbound and client
cursor.execute("SELECT id, settings, port FROM inbounds WHERE protocol='vless' LIMIT 1")
row = cursor.fetchone()
if not row:
    print("❌ VLESS inbound not found")
    exit(1)

inbound_id, settings_json, port = row
settings = json.loads(settings_json)

# Find admin client
admin_client = None
for client in settings.get('clients', []):
    if client['email'] == f'trial_{ADMIN_TELEGRAM_ID}':
        admin_client = client
        break

if not admin_client:
    print(f"❌ Client trial_{ADMIN_TELEGRAM_ID} not found")
    exit(1)

# Generate VLESS URL
server_ip = "89.44.76.190"
display_name = "⚡ VLESS-Reality | Netherlands 🇳🇱"
client_uuid = admin_client['id']

vless_url = (
    f"vless://{client_uuid}@{server_ip}:{port}"
    f"?type=tcp&security=reality&pbk=c4d33NKVpulPMhdJOcq-e12fjJjRZMU5V_wTTIm5K2c"
    f"&fp=chrome&sni=www.google.com&sid=0123456789abcdef&spx=%2F"
    f"&flow=xtls-rprx-vision"
    f"#{quote(display_name)}"
)

expiry_date = datetime.fromtimestamp(admin_client['expiryTime'] / 1000)
traffic_gb = admin_client.get('totalGB', 0) / (1024**3)

print("=== Текущий VPN ключ ===\n")
print(f"Email:    {admin_client['email']}")
print(f"UUID:     {client_uuid}")
print(f"Срок:     до {expiry_date.strftime('%Y-%m-%d %H:%M:%S')} UTC")
print(f"Трафик:   {traffic_gb:.1f} GB")
print(f"Flow:     {admin_client.get('flow', 'none')}")
print(f"Порт:     {port}")
print(f"\nVLESS URL:")
print(vless_url)

conn.close()

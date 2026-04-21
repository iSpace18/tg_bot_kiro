#!/usr/bin/env python3
import sqlite3
import json

DB_PATH = "/etc/x-ui/x-ui.db"
CONFIG_PATH = "/usr/local/x-ui/bin/config.json"

print("=== Fixing VPN Issues ===\n")

# 1. Enable access logs in config.json
print("1. Enabling access logs for statistics...")
with open(CONFIG_PATH, 'r') as f:
    config = json.load(f)

# Enable access logging
config['log']['access'] = '/var/log/xray/access.log'
config['log']['loglevel'] = 'warning'

with open(CONFIG_PATH, 'w') as f:
    json.dump(config, f, indent=2)

print("   ✅ Access log enabled: /var/log/xray/access.log")

# 2. Create log directory
import os
os.makedirs('/var/log/xray', exist_ok=True)
print("   ✅ Log directory created")

# 3. Update database settings
print("\n2. Updating inbound settings in database...")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get current inbound
cursor.execute("SELECT id, remark, listen, port, protocol, settings, stream_settings FROM inbounds WHERE protocol='vless' LIMIT 1")
row = cursor.fetchone()
if not row:
    print("   ❌ VLESS inbound not found")
    exit(1)

inbound_id, remark, listen, port, protocol, settings_json, stream_settings_json = row

# Update remark (display name)
new_remark = "⚡ VLESS-Reality | Netherlands 🇳🇱"
cursor.execute("UPDATE inbounds SET remark=? WHERE id=?", (new_remark, inbound_id))
print(f"   ✅ Updated display name: {new_remark}")

# Update sniffing to enable statistics
stream_settings = json.loads(stream_settings_json)
if 'sniffing' not in stream_settings:
    stream_settings['sniffing'] = {}

stream_settings['sniffing'] = {
    "enabled": True,
    "destOverride": ["http", "tls", "quic", "fakedns"],
    "metadataOnly": False,
    "routeOnly": False
}

cursor.execute("UPDATE inbounds SET stream_settings=? WHERE id=?", (json.dumps(stream_settings), inbound_id))
print("   ✅ Sniffing enabled for traffic tracking")

conn.commit()
conn.close()

print("\n3. Summary:")
print(f"   - Inbound ID: {inbound_id}")
print(f"   - Display name: {new_remark}")
print(f"   - Port: {port}")
print(f"   - Access log: /var/log/xray/access.log")
print(f"   - Statistics: Enabled")

print("\n✅ All fixes applied! Restart x-ui to apply changes:")
print("   systemctl restart x-ui")

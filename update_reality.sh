#!/bin/bash

# Update x-ui database with Reality configuration
DB_PATH="/etc/x-ui/x-ui.db"

# Get inbound ID
INBOUND_ID=$(sqlite3 $DB_PATH "SELECT id FROM inbounds WHERE protocol='vless' LIMIT 1;")

if [ -z "$INBOUND_ID" ]; then
    echo "Error: VLESS inbound not found"
    exit 1
fi

echo "Found VLESS inbound ID: $INBOUND_ID"

# Get current settings
SETTINGS=$(sqlite3 $DB_PATH "SELECT settings FROM inbounds WHERE id=$INBOUND_ID;")
STREAM_SETTINGS=$(sqlite3 $DB_PATH "SELECT stream_settings FROM inbounds WHERE id=$INBOUND_ID;")

echo "Current settings retrieved"

# Update stream settings with Reality
NEW_STREAM_SETTINGS='{
  "network": "tcp",
  "security": "reality",
  "externalProxy": [],
  "realitySettings": {
    "show": false,
    "xver": 0,
    "dest": "www.google.com:443",
    "serverNames": ["www.google.com", "google.com"],
    "privateKey": "MPnNzbMLF812adXAeJXYv3nY3M6gDWZJsc2kIlLAZnE",
    "minClient": "",
    "maxClient": "",
    "maxTimediff": 0,
    "shortIds": ["", "0123456789abcdef"],
    "settings": {
      "publicKey": "c4d33NKVpulPMhdJOcq-e12fjJjRZMU5V_wTTIm5K2c",
      "fingerprint": "chrome",
      "serverName": "",
      "spiderX": "/"
    }
  },
  "tcpSettings": {
    "acceptProxyProtocol": false,
    "header": {
      "type": "none"
    }
  },
  "sockopt": {
    "dialerProxy": "",
    "acceptProxyProtocol": false,
    "tcpFastOpen": true,
    "tcpKeepAliveIdle": 100,
    "tcpKeepAliveInterval": 10,
    "tcpNoDelay": true,
    "tcpCongestion": "bbr",
    "tcpMptcp": false,
    "mark": 255
  }
}'

# Update database
sqlite3 $DB_PATH "UPDATE inbounds SET stream_settings='$NEW_STREAM_SETTINGS' WHERE id=$INBOUND_ID;"

echo "Stream settings updated with Reality"

# Update all clients to add flow
python3 << 'PYTHON_SCRIPT'
import sqlite3
import json

DB_PATH = "/etc/x-ui/x-ui.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get inbound ID
cursor.execute("SELECT id, settings FROM inbounds WHERE protocol='vless' LIMIT 1")
row = cursor.fetchone()
if not row:
    print("Error: VLESS inbound not found")
    exit(1)

inbound_id, settings_json = row
settings = json.loads(settings_json)

# Update all clients with flow
if "clients" in settings:
    for client in settings["clients"]:
        client["flow"] = "xtls-rprx-vision"
    
    # Save updated settings
    cursor.execute("UPDATE inbounds SET settings=? WHERE id=?", (json.dumps(settings), inbound_id))
    conn.commit()
    print(f"Updated {len(settings['clients'])} clients with flow=xtls-rprx-vision")
else:
    print("No clients found")

conn.close()
PYTHON_SCRIPT

echo "All clients updated with Vision flow"

# Restart x-ui
systemctl restart x-ui
sleep 3

echo "x-ui restarted"
systemctl status x-ui --no-pager | head -15

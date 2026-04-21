#!/usr/bin/env python3
import sqlite3
import json

DB_PATH = "/etc/x-ui/x-ui.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("SELECT settings FROM inbounds WHERE protocol='vless' LIMIT 1")
row = cursor.fetchone()
settings = json.loads(row[0])

print(f"Total clients: {len(settings['clients'])}")
print("\nClients:")
for i, client in enumerate(settings['clients'], 1):
    print(f"{i}. {client['email']} - flow: {client.get('flow', 'none')}")

conn.close()

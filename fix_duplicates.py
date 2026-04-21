#!/usr/bin/env python3
import sqlite3
import json

DB_PATH = "/etc/x-ui/x-ui.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get VLESS inbound
cursor.execute("SELECT id, settings FROM inbounds WHERE protocol='vless' LIMIT 1")
row = cursor.fetchone()
if not row:
    print("Error: VLESS inbound not found")
    exit(1)

inbound_id, settings_json = row
settings = json.loads(settings_json)

# Remove duplicates by email
if "clients" in settings:
    seen_emails = set()
    unique_clients = []
    duplicates = []
    
    for client in settings["clients"]:
        email = client.get("email")
        if email not in seen_emails:
            seen_emails.add(email)
            unique_clients.append(client)
        else:
            duplicates.append(email)
    
    print(f"Found {len(settings['clients'])} total clients")
    print(f"Found {len(duplicates)} duplicates: {duplicates}")
    print(f"Keeping {len(unique_clients)} unique clients")
    
    # Update with unique clients only
    settings["clients"] = unique_clients
    cursor.execute("UPDATE inbounds SET settings=? WHERE id=?", (json.dumps(settings), inbound_id))
    conn.commit()
    print("Database updated successfully")
else:
    print("No clients found")

conn.close()

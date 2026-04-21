#!/usr/bin/env python3
"""Delete old trial client that doesn't have statistics tracking."""

import sqlite3
import json

DB_PATH = "/etc/x-ui/x-ui.db"
CLIENT_EMAIL = "trial_1658346274"

def delete_client():
    """Delete client from inbound settings and client_traffics."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        
        # Get inbound settings
        cursor.execute("SELECT id, settings FROM inbounds WHERE id=1")
        row = cursor.fetchone()
        if not row:
            print("ERROR: Inbound not found")
            return False
        
        inbound_id, settings_str = row
        settings = json.loads(settings_str)
        clients = settings.get('clients', [])
        
        # Find and remove client
        original_count = len(clients)
        clients = [c for c in clients if c.get('email') != CLIENT_EMAIL]
        new_count = len(clients)
        
        if original_count == new_count:
            print(f"❌ Client {CLIENT_EMAIL} not found in inbound settings")
            return False
        
        # Update settings
        settings['clients'] = clients
        cursor.execute(
            "UPDATE inbounds SET settings = ? WHERE id = ?",
            (json.dumps(settings), inbound_id)
        )
        
        # Delete from client_traffics if exists
        cursor.execute("DELETE FROM client_traffics WHERE email = ?", (CLIENT_EMAIL,))
        
        conn.commit()
        
        print(f"✅ Client {CLIENT_EMAIL} deleted successfully!")
        print(f"   Removed from inbound settings: {original_count} -> {new_count} clients")
        print(f"   Removed from client_traffics: {cursor.rowcount} rows")
        
        return True
        
    finally:
        conn.close()

if __name__ == "__main__":
    delete_client()

#!/usr/bin/env python3
"""List all clients and check their statistics tracking."""

import sqlite3
import json

DB_PATH = "/etc/x-ui/x-ui.db"

def list_clients():
    """List all clients from inbound settings and client_traffics."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        
        # Get clients from inbound settings
        cursor.execute("SELECT settings FROM inbounds WHERE id=1")
        row = cursor.fetchone()
        if not row:
            print("ERROR: Inbound not found")
            return
        
        settings = json.loads(row[0])
        inbound_clients = settings.get('clients', [])
        
        print(f"\n📋 Total clients in inbound settings: {len(inbound_clients)}")
        print("=" * 80)
        
        # Get clients from client_traffics
        cursor.execute("SELECT email FROM client_traffics")
        tracked_emails = {row[0] for row in cursor.fetchall()}
        
        print(f"\n✅ Clients with statistics tracking: {len(tracked_emails)}")
        print("=" * 80)
        
        # Compare
        for i, client in enumerate(inbound_clients, 1):
            email = client.get('email', 'N/A')
            uuid = client.get('id', 'N/A')
            has_tracking = email in tracked_emails
            
            status = "✅ HAS STATS" if has_tracking else "❌ NO STATS"
            print(f"\n{i}. {email}")
            print(f"   UUID: {uuid}")
            print(f"   Status: {status}")
            
            if has_tracking:
                # Get traffic stats
                cursor.execute(
                    "SELECT up, down, enable FROM client_traffics WHERE email=?",
                    (email,)
                )
                traffic_row = cursor.fetchone()
                if traffic_row:
                    up, down, enable = traffic_row
                    total_gb = (up + down) / (1024**3)
                    print(f"   Traffic: {total_gb:.4f} GB (↑{up/1024**2:.2f} MB, ↓{down/1024**2:.2f} MB)")
                    print(f"   Enabled: {bool(enable)}")
        
        # Find clients without tracking
        missing_tracking = [c for c in inbound_clients if c.get('email') not in tracked_emails]
        if missing_tracking:
            print(f"\n\n⚠️  WARNING: {len(missing_tracking)} clients WITHOUT statistics tracking:")
            for client in missing_tracking:
                print(f"   - {client.get('email')}")
        else:
            print(f"\n\n✅ All clients have statistics tracking enabled!")
        
    finally:
        conn.close()

if __name__ == "__main__":
    list_clients()

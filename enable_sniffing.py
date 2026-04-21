#!/usr/bin/env python3
"""Enable sniffing for x-ui inbound to fix statistics tracking."""

import sqlite3
import json

DB_PATH = "/etc/x-ui/x-ui.db"

def enable_sniffing():
    """Enable sniffing for VLESS inbound."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        
        # Get current inbound configuration
        cursor.execute("SELECT id, sniffing FROM inbounds WHERE protocol='vless'")
        row = cursor.fetchone()
        
        if not row:
            print("ERROR: VLESS inbound not found")
            return False
        
        inbound_id, current_sniffing = row
        print(f"Current sniffing config: {current_sniffing}")
        
        # Enable sniffing
        new_sniffing = {
            "enabled": True,
            "destOverride": ["http", "tls", "quic", "fakedns"],
            "metadataOnly": False,
            "routeOnly": False
        }
        
        cursor.execute(
            "UPDATE inbounds SET sniffing = ? WHERE id = ?",
            (json.dumps(new_sniffing), inbound_id)
        )
        conn.commit()
        
        print(f"✅ Sniffing enabled for inbound {inbound_id}")
        print(f"New sniffing config: {json.dumps(new_sniffing, indent=2)}")
        
        return True
        
    finally:
        conn.close()

if __name__ == "__main__":
    enable_sniffing()

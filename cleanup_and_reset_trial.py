#!/usr/bin/env python3
"""
Cleanup all test users and reset trial flag for admin user.
"""

import sqlite3
import json

XUI_DB_PATH = "/etc/x-ui/x-ui.db"
BOT_DB_PATH = "/opt/vpn_bot/data/bot.db"
ADMIN_ID = 1658346274

def cleanup_xui_clients():
    """Remove all test clients from x-ui."""
    conn = sqlite3.connect(XUI_DB_PATH)
    try:
        cursor = conn.cursor()
        
        # Get inbound settings
        cursor.execute("SELECT id, settings FROM inbounds WHERE id=1")
        row = cursor.fetchone()
        if not row:
            print("ERROR: Inbound not found")
            return
        
        inbound_id, settings_str = row
        settings = json.loads(settings_str)
        clients = settings.get('clients', [])
        
        print(f"\n📋 Current clients in x-ui: {len(clients)}")
        for client in clients:
            print(f"   - {client.get('email')}")
        
        # Remove ALL clients
        settings['clients'] = []
        cursor.execute(
            "UPDATE inbounds SET settings = ? WHERE id = ?",
            (json.dumps(settings), inbound_id)
        )
        
        # Clear client_traffics table
        cursor.execute("DELETE FROM client_traffics")
        deleted_traffics = cursor.rowcount
        
        conn.commit()
        
        print(f"\n✅ Removed {len(clients)} clients from x-ui")
        print(f"✅ Removed {deleted_traffics} entries from client_traffics")
        
    finally:
        conn.close()

def reset_trial_flag():
    """Reset trial flag for admin user in bot database."""
    conn = sqlite3.connect(BOT_DB_PATH)
    try:
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id, trial_used FROM users WHERE telegram_id=?", (ADMIN_ID,))
        row = cursor.fetchone()
        
        if not row:
            print(f"\n⚠️  User {ADMIN_ID} not found in bot database")
            return
        
        user_id, trial_used = row
        print(f"\n👤 User {ADMIN_ID} found:")
        print(f"   Trial used: {bool(trial_used)}")
        
        # Reset trial_used flag
        cursor.execute("UPDATE users SET trial_used = 0 WHERE telegram_id = ?", (ADMIN_ID,))
        
        # Delete from trial_usage table
        cursor.execute("DELETE FROM trial_usage WHERE telegram_id = ?", (ADMIN_ID,))
        deleted_usage = cursor.rowcount
        
        conn.commit()
        
        print(f"\n✅ Reset trial_used flag for user {ADMIN_ID}")
        print(f"✅ Removed {deleted_usage} entries from trial_usage")
        
    finally:
        conn.close()

def main():
    """Main cleanup function."""
    print("=" * 80)
    print("🧹 CLEANUP: Removing all test users and resetting trial flag")
    print("=" * 80)
    
    # Cleanup x-ui clients
    cleanup_xui_clients()
    
    # Reset trial flag
    reset_trial_flag()
    
    print("\n" + "=" * 80)
    print("✅ CLEANUP COMPLETE!")
    print("=" * 80)
    print("\n📱 You can now request trial subscription through the bot")
    print(f"   Telegram ID: {ADMIN_ID}")
    print("   Trial flag: RESET ✅")
    print("   All test users: REMOVED ✅")

if __name__ == "__main__":
    main()

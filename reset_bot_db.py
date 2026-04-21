#!/usr/bin/env python3
import sqlite3
from datetime import datetime

BOT_DB_PATH = "/opt/vpn_bot/data/bot.db"
ADMIN_TELEGRAM_ID = 1658346274

conn = sqlite3.connect(BOT_DB_PATH)
cursor = conn.cursor()

# Check current state
cursor.execute("SELECT COUNT(*) FROM users")
user_count = cursor.fetchone()[0]
print(f"Current users in bot DB: {user_count}")

# Reset trial_used for admin user
cursor.execute("""
    UPDATE users 
    SET trial_used = 0
    WHERE telegram_id = ?
""", (ADMIN_TELEGRAM_ID,))

affected = cursor.rowcount
conn.commit()

if affected > 0:
    print(f"✅ Reset trial period for user {ADMIN_TELEGRAM_ID}")
else:
    print(f"ℹ️  User {ADMIN_TELEGRAM_ID} not found in database (will be created on first /start)")

# Show admin user info
cursor.execute("SELECT telegram_id, username, trial_used, created_at FROM users WHERE telegram_id = ?", (ADMIN_TELEGRAM_ID,))
row = cursor.fetchone()
if row:
    print(f"\nAdmin user info:")
    print(f"  Telegram ID: {row[0]}")
    print(f"  Username: {row[1]}")
    print(f"  Trial used: {row[2]}")
    print(f"  Created: {row[3]}")

conn.close()
print("\n✅ Bot database updated!")

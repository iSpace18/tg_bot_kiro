#!/usr/bin/env python3
import sqlite3

BOT_DB_PATH = "/opt/vpn_bot/data/bot.db"
ADMIN_TELEGRAM_ID = 1658346274

print("=== Полный сброс пробного периода ===\n")

conn = sqlite3.connect(BOT_DB_PATH)
cursor = conn.cursor()

# 1. Reset users.trial_used
print("1. Сброс users.trial_used...")
cursor.execute("UPDATE users SET trial_used = 0 WHERE telegram_id = ?", (ADMIN_TELEGRAM_ID,))
affected1 = cursor.rowcount
print(f"   ✅ Обновлено записей в users: {affected1}")

# 2. Delete from trial_usage table
print("\n2. Удаление из trial_usage...")
cursor.execute("DELETE FROM trial_usage WHERE telegram_id = ?", (ADMIN_TELEGRAM_ID,))
affected2 = cursor.rowcount
print(f"   ✅ Удалено записей из trial_usage: {affected2}")

conn.commit()

# 3. Verify
print("\n3. Проверка:")
cursor.execute("SELECT telegram_id, username, trial_used FROM users WHERE telegram_id = ?", (ADMIN_TELEGRAM_ID,))
user_row = cursor.fetchone()
if user_row:
    print(f"   users.trial_used = {user_row[2]}")

cursor.execute("SELECT COUNT(*) FROM trial_usage WHERE telegram_id = ?", (ADMIN_TELEGRAM_ID,))
trial_count = cursor.fetchone()[0]
print(f"   trial_usage записей = {trial_count}")

if user_row and user_row[2] == 0 and trial_count == 0:
    print("\n   ✅ Пробный период полностью сброшен!")
    print("   Теперь можно получить пробный период через бота.")
else:
    print("\n   ⚠️  Что-то пошло не так:")
    print(f"      users.trial_used = {user_row[2] if user_row else 'N/A'} (должно быть 0)")
    print(f"      trial_usage записей = {trial_count} (должно быть 0)")

conn.close()

print("\n✅ Готово!")

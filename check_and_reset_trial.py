#!/usr/bin/env python3
import sqlite3

BOT_DB_PATH = "/opt/vpn_bot/data/bot.db"
ADMIN_TELEGRAM_ID = 1658346274

print("=== Проверка и сброс пробного периода ===\n")

conn = sqlite3.connect(BOT_DB_PATH)
cursor = conn.cursor()

# Check current state
print("1. Текущее состояние:")
cursor.execute("SELECT telegram_id, username, trial_used, created_at FROM users WHERE telegram_id = ?", (ADMIN_TELEGRAM_ID,))
row = cursor.fetchone()

if row:
    print(f"   Telegram ID: {row[0]}")
    print(f"   Username: {row[1]}")
    print(f"   Trial used: {row[2]}")
    print(f"   Created: {row[3]}")
else:
    print(f"   ⚠️  Пользователь {ADMIN_TELEGRAM_ID} не найден в базе")

# Reset trial_used
print("\n2. Сброс пробного периода...")
cursor.execute("UPDATE users SET trial_used = 0 WHERE telegram_id = ?", (ADMIN_TELEGRAM_ID,))
affected = cursor.rowcount
conn.commit()

if affected > 0:
    print(f"   ✅ Обновлено записей: {affected}")
else:
    print(f"   ⚠️  Записи не обновлены (пользователь не найден)")

# Verify
print("\n3. Проверка после сброса:")
cursor.execute("SELECT telegram_id, username, trial_used FROM users WHERE telegram_id = ?", (ADMIN_TELEGRAM_ID,))
row = cursor.fetchone()

if row:
    print(f"   Telegram ID: {row[0]}")
    print(f"   Username: {row[1]}")
    print(f"   Trial used: {row[2]}")
    
    if row[2] == 0:
        print("\n   ✅ Пробный период успешно сброшен!")
    else:
        print(f"\n   ❌ Ошибка: trial_used = {row[2]} (должно быть 0)")
else:
    print("   ❌ Пользователь не найден после обновления")

# Show all users for debugging
print("\n4. Все пользователи в базе:")
cursor.execute("SELECT telegram_id, username, trial_used FROM users")
rows = cursor.fetchall()
for r in rows:
    print(f"   ID: {r[0]}, Username: {r[1]}, Trial used: {r[2]}")

conn.close()

print("\n✅ Готово! Теперь попробуйте получить пробный период через бота.")

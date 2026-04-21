#!/usr/bin/env python3
import sqlite3
import json
import uuid
from datetime import datetime, timedelta

XUI_DB_PATH = "/etc/x-ui/x-ui.db"
BOT_DB_PATH = "/opt/vpn_bot/data/bot.db"
ADMIN_TELEGRAM_ID = 1658346274

print("=== Сброс пробного периода ===\n")

# 1. Reset bot database
print("1. Сброс базы данных бота...")
bot_conn = sqlite3.connect(BOT_DB_PATH)
bot_cursor = bot_conn.cursor()

bot_cursor.execute("UPDATE users SET trial_used = 0 WHERE telegram_id = ?", (ADMIN_TELEGRAM_ID,))
bot_conn.commit()
print(f"   ✅ Пробный период сброшен для пользователя {ADMIN_TELEGRAM_ID}")

bot_cursor.execute("SELECT telegram_id, username, trial_used FROM users WHERE telegram_id = ?", (ADMIN_TELEGRAM_ID,))
row = bot_cursor.fetchone()
if row:
    print(f"   Пользователь: {row[1]} (ID: {row[0]})")
    print(f"   Trial used: {row[2]}")

bot_conn.close()

# 2. Delete old client and create new one
print("\n2. Обновление VPN клиента...")
xui_conn = sqlite3.connect(XUI_DB_PATH)
xui_cursor = xui_conn.cursor()

# Get inbound
xui_cursor.execute("SELECT id, settings, port FROM inbounds WHERE protocol='vless' LIMIT 1")
row = xui_cursor.fetchone()
if not row:
    print("   ❌ VLESS inbound not found")
    exit(1)

inbound_id, settings_json, port = row
settings = json.loads(settings_json)

old_count = len(settings.get('clients', []))
print(f"   Старых клиентов: {old_count}")

# Create new client
new_uuid = str(uuid.uuid4())
expiry_ts = int((datetime.utcnow() + timedelta(days=3)).timestamp() * 1000)

new_client = {
    "id": new_uuid,
    "email": f"trial_{ADMIN_TELEGRAM_ID}",
    "flow": "xtls-rprx-vision",
    "enable": True,
    "expiryTime": expiry_ts,
    "totalGB": 10737418240,  # 10 GB
    "limitIp": 1
}

# Replace all clients with new one
settings["clients"] = [new_client]

xui_cursor.execute("UPDATE inbounds SET settings=? WHERE id=?", (json.dumps(settings), inbound_id))
xui_conn.commit()

print(f"   ✅ Удалены все старые клиенты")
print(f"   ✅ Создан новый клиент:")
print(f"      Email: trial_{ADMIN_TELEGRAM_ID}")
print(f"      UUID: {new_uuid}")
print(f"      Срок: до {datetime.fromtimestamp(expiry_ts / 1000).strftime('%Y-%m-%d %H:%M:%S')} UTC")
print(f"      Трафик: 10 GB")

# Generate VLESS URL
server_ip = "89.44.76.190"
display_name = "⚡ VLESS-Reality | Netherlands 🇳🇱"
from urllib.parse import quote

vless_url = (
    f"vless://{new_uuid}@{server_ip}:{port}"
    f"?type=tcp&security=reality&pbk=c4d33NKVpulPMhdJOcq-e12fjJjRZMU5V_wTTIm5K2c"
    f"&fp=chrome&sni=www.google.com&sid=0123456789abcdef&spx=%2F"
    f"&flow=xtls-rprx-vision"
    f"#{quote(display_name)}"
)

print(f"\n3. Новый VLESS ключ:")
print(vless_url)

xui_conn.close()

print("\n✅ Готово! Перезапустите x-ui:")
print("   systemctl restart x-ui")

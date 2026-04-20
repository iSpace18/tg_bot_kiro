import paramiko
import time

HOST = "89.44.76.190"
USER = "root"
PASS = "Mb69Bs5T18hNvrw5FC"

# Исправленный profile handler
profile_content = '''import logging
from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.orm import Session
from sqlalchemy import select

from bot.models import User, VPNKey

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "👤 Профиль")
async def profile_info(message: Message, session: Session):
    result = session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("Сначала отправьте /start")
        return

    result = session.execute(select(VPNKey).where(VPNKey.user_id == user.id, VPNKey.is_active == True))
    active_keys = result.scalars().all()

    await message.answer(
        f"👤 <b>Ваш профиль</b>\\n\\n"
        f"🆔 ID: {user.telegram_id}\\n"
        f"🔑 Активных ключей: {len(active_keys)}\\n"
        f"🎁 Пробный период: {'Использован' if user.trial_used else 'Доступен'}",
        parse_mode="HTML"
    )
'''

# Исправленный support handler
support_content = '''import logging
from aiogram import Router, F
from aiogram.types import Message

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "🆘 Поддержка")
async def support_info(message: Message):
    await message.answer(
        "🆘 <b>Поддержка</b>\\n\\n"
        "📧 Email: support@example.com\\n"
        "💬 Telegram: @support\\n\\n"
        "Мы ответим в течение 24 часов!",
        parse_mode="HTML"
    )
'''

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=30)

def run(cmd, timeout=60):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out)
    if err and "warning" not in err.lower():
        print("STDERR:", err)
    return out.strip()

print("=== Update profile.py ===")
stdin, stdout, stderr = client.exec_command("cat > /root/vpn_telegram/bot/handlers/profile.py")
stdin.write(profile_content)
stdin.close()

print("=== Update support.py ===")
stdin, stdout, stderr = client.exec_command("cat > /root/vpn_telegram/bot/handlers/support.py")
stdin.write(support_content)
stdin.close()

print("=== Fix payment.py - trial period ===")
# Исправить проверку trial_used
run("sed -i 's/select(TrialUsage).where(TrialUsage.telegram_id/select(User).where(User.telegram_id/g' /root/vpn_telegram/bot/handlers/payment.py")

print("\\n✅ All handlers updated")

print("\\n=== Restart bot ===")
run("docker rm -f vpn_telegram_bot")
run("find /root/vpn_telegram -name '*.pyc' -delete")
run("find /root/vpn_telegram -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true")
run("docker run -d --name vpn_telegram_bot --restart unless-stopped --env-file /root/vpn_telegram/.env -v /root/vpn_telegram:/app -v /root/vpn_telegram/data:/app/data -v /etc/x-ui:/etc/x-ui:rw --network host --pid host --privileged -w /app vpn_telegram-bot:working python -m bot.main")

time.sleep(25)

print("\\n=== Check logs ===")
logs = run("docker logs vpn_telegram_bot --tail=50")

if "Bot starting" in logs:
    print("\\n✅ БОТ ЗАПУЩЕН!")
    # Проверим ошибки
    errors = run("docker logs vpn_telegram_bot 2>&1 | grep -c 'Error\\|Traceback'")
    if errors and int(errors) > 0:
        print(f"⚠️ Найдено ошибок: {errors}")
        run("docker logs vpn_telegram_bot --tail=30 2>&1 | grep -A 3 'Error'")
    else:
        print("✅ Нет ошибок!")
else:
    print("❌ Проблемы с запуском")

print("\\n=== Status ===")
run("docker ps | grep vpn")

print("\\n🎉 Проверьте бота:")
print("• 👤 Профиль")
print("• 🆘 Поддержка")
print("• 🎁 Пробный период")
print("• 💳 Купить VPN → ЮKassa")

client.close()
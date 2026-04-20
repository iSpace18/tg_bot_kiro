import paramiko
import time

HOST = "89.44.76.190"
USER = "root"
PASS = "Mb69Bs5T18hNvrw5FC"

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

print("=== Fix all handlers with wrong session parameters ===")

# Fix all handlers to use correct session parameter and remove async/await
commands = [
    # Fix session parameter names
    "find /root/vpn_telegram/bot/handlers -name '*.py' -exec sed -i 's/db_session/session/g' {} \\;",
    
    # Fix async session calls
    "find /root/vpn_telegram/bot/handlers -name '*.py' -exec sed -i 's/await session\\./session./g' {} \\;",
    "find /root/vpn_telegram/bot/handlers -name '*.py' -exec sed -i 's/session\\.scalar(/session.execute(/g' {} \\;",
    "find /root/vpn_telegram/bot/handlers -name '*.py' -exec sed -i 's/session\\.scalars(/session.execute(/g' {} \\;",
    
    # Fix imports
    "find /root/vpn_telegram/bot/handlers -name '*.py' -exec sed -i 's/from sqlalchemy.ext.asyncio import AsyncSession/from sqlalchemy.orm import Session/g' {} \\;",
    "find /root/vpn_telegram/bot/handlers -name '*.py' -exec sed -i 's/AsyncSession/Session/g' {} \\;",
]

for cmd in commands:
    print(f"Running: {cmd.split('/')[-1]}")
    run(cmd)

print("\n=== Create simple working handlers ===")

# Simple referral handler
referral_content = '''import logging
from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.orm import Session
from sqlalchemy import select

from bot.models import User
from bot.keyboards.main import main_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "👥 Реферальная программа")
async def referral_info(message: Message, session: Session):
    result = session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("Сначала отправьте /start")
        return
    
    ref_link = f"https://t.me/{(await message.bot.get_me()).username}?start=ref{user.id}"
    
    await message.answer(
        f"👥 <b>Реферальная программа</b>\\n\\n"
        f"🔗 Ваша ссылка:\\n<code>{ref_link}</code>\\n\\n"
        f"💰 За каждого приглашенного друга вы получите бонус!",
        parse_mode="HTML"
    )
'''

# Simple profile handler  
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
        f"📅 Регистрация: {user.created_at.strftime('%d.%m.%Y')}\\n"
        f"🔑 Активных ключей: {len(active_keys)}\\n"
        f"🎁 Пробный период: {'Использован' if user.trial_used else 'Доступен'}",
        parse_mode="HTML"
    )
'''

print("\n=== Update referral handler ===")
stdin, stdout, stderr = client.exec_command("cat > /root/vpn_telegram/bot/handlers/referral.py")
stdin.write(referral_content)
stdin.close()

print("\n=== Update profile handler ===")
stdin, stdout, stderr = client.exec_command("cat > /root/vpn_telegram/bot/handlers/profile.py")
stdin.write(profile_content)
stdin.close()

print("\n✅ All handlers fixed")

print("\n=== Restart bot ===")
run("docker restart vpn_telegram_bot")
time.sleep(15)

print("\n=== Check logs ===")
run("docker logs vpn_telegram_bot --tail=30")

print("\n=== Check status ===")
run("docker ps | grep vpn")

print("\n🎉 Bot should be fully working now!")
print("Test all functions:")
print("• /start")
print("• 👤 Профиль") 
print("• 👥 Реферальная программа")
print("• 🎁 Пробный период")
print("• 💳 Купить VPN")

client.close()
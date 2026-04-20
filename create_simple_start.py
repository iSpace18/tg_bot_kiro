import paramiko
import time

HOST = "89.44.76.190"
USER = "root"
PASS = "Mb69Bs5T18hNvrw5FC"

# Simple working start handler
start_content = '''import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.orm import Session
from sqlalchemy import select

from bot.models import User
from bot.keyboards.main import main_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()


def get_or_create_user(telegram_id: int, username: str, full_name: str, session: Session) -> User:
    result = session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(telegram_id=telegram_id, username=username, full_name=full_name)
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


@router.message(CommandStart())
async def cmd_start(message: Message, session: Session):
    user = get_or_create_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name or "",
        session,
    )

    await message.answer(
        f"👋 Привет, <b>{message.from_user.first_name}</b>!\\n\\n"
        "🔐 Я бот для продажи VPN-доступа.\\n\\n"
        "Выбери нужный раздел в меню ниже:",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "Главное меню. Выбери раздел:",
    )
    await callback.answer()
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

print("=== Create simple start handler ===")
stdin, stdout, stderr = client.exec_command("cat > /root/vpn_telegram/bot/handlers/start.py")
stdin.write(start_content)
stdin.close()

print("✅ Simple start handler created")

print("\n=== Restart bot ===")
run("docker restart vpn_telegram_bot")
time.sleep(15)

print("\n=== Check logs ===")
run("docker logs vpn_telegram_bot --tail=30")

print("\n=== Final status ===")
run("docker ps | grep vpn")

print("\n🎉 Bot should be working now! Test /start command!")

client.close()
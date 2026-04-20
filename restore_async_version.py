import paramiko
import time

HOST = "89.44.76.190"
USER = "root"
PASS = "Mb69Bs5T18hNvrw5FC"

# Restore async versions
db_content = '''import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from bot.models import Base
from bot.config import settings

os.makedirs("data", exist_ok=True)

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
'''

middleware_content = '''from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from bot.utils.db import AsyncSessionLocal


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with AsyncSessionLocal() as session:
            data["session"] = session
            return await handler(event, data)
'''

main_content = '''import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.utils.db import init_db
from bot.utils.logger import setup_logger
from bot.middlewares.database import DatabaseMiddleware
from bot.handlers import start, payment, profile, referral, support, admin, faq

setup_logger()
logger = logging.getLogger(__name__)


async def seed_default_plans(session):
    """Insert default plans if none exist."""
    from sqlalchemy import select
    from bot.models import Plan
    result = await session.execute(select(Plan))
    if result.scalars().first():
        return

    default_plans = [
        Plan(name="1 день",    duration_days=1,   price_stars=15,  price_rub=50,   traffic_limit_gb=0),
        Plan(name="1 неделя",  duration_days=7,   price_stars=75,  price_rub=250,  traffic_limit_gb=0),
        Plan(name="1 месяц",   duration_days=30,  price_stars=250, price_rub=350,  traffic_limit_gb=0),
        Plan(name="6 месяцев", duration_days=180, price_stars=999, price_rub=1500, traffic_limit_gb=0),
        Plan(name="1 год",     duration_days=365, price_stars=1800, price_rub=2500, traffic_limit_gb=0),
    ]
    for plan in default_plans:
        session.add(plan)
    await session.commit()
    logger.info("Default plans seeded.")


async def main():
    await init_db()

    # Seed default plans
    from bot.utils.db import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await seed_default_plans(session)

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Register middleware
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())

    # Register routers
    dp.include_router(start.router)
    dp.include_router(payment.router)
    dp.include_router(profile.router)
    dp.include_router(referral.router)
    dp.include_router(support.router)
    dp.include_router(admin.router)
    dp.include_router(faq.router)

    logger.info("Bot starting...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
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

print("=== Restore async DATABASE_URL ===")
run("sed -i 's|DATABASE_URL=.*|DATABASE_URL=sqlite+aiosqlite:///data/bot.db|' /root/vpn_telegram/.env")

print("\n=== Update db.py ===")
stdin, stdout, stderr = client.exec_command("cat > /root/vpn_telegram/bot/utils/db.py")
stdin.write(db_content)
stdin.close()

print("\n=== Update middleware ===")
stdin, stdout, stderr = client.exec_command("cat > /root/vpn_telegram/bot/middlewares/database.py")
stdin.write(middleware_content)
stdin.close()

print("\n=== Update main.py ===")
stdin, stdout, stderr = client.exec_command("cat > /root/vpn_telegram/bot/main.py")
stdin.write(main_content)
stdin.close()

print("\n✅ All files restored to async versions")

print("\n=== Restart bot ===")
run("docker restart vpn_telegram_bot")
time.sleep(15)

print("\n=== Check logs ===")
run("docker logs vpn_telegram_bot --tail=50")

print("\n=== Check status ===")
run("docker ps | grep vpn")

print("\n🎉 Bot should be working now with aiosqlite properly installed!")
client.close()
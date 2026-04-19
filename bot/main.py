import asyncio
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

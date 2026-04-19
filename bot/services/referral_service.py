import random
import string
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.models import User, ReferralBonus
from bot.config import settings

logger = logging.getLogger(__name__)


def generate_referral_code(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


async def get_or_create_referral_code(user: User, session: AsyncSession) -> str:
    if not user.referral_code:
        code = generate_referral_code()
        # Ensure uniqueness
        while True:
            result = await session.execute(select(User).where(User.referral_code == code))
            if not result.scalar_one_or_none():
                break
            code = generate_referral_code()
        user.referral_code = code
        await session.commit()
    return user.referral_code


async def process_referral(new_user: User, referral_code: str, session: AsyncSession):
    """Credit referrer with bonus days when referred user makes first purchase."""
    result = await session.execute(
        select(User).where(User.referral_code == referral_code)
    )
    referrer = result.scalar_one_or_none()
    if not referrer or referrer.telegram_id == new_user.telegram_id:
        return

    new_user.referred_by = referrer.telegram_id
    bonus = ReferralBonus(
        user_id=referrer.id,
        referred_telegram_id=new_user.telegram_id,
        bonus_days=settings.REFERRAL_BONUS_PERCENT,
    )
    session.add(bonus)
    await session.commit()
    logger.info(f"Referral bonus added for user {referrer.telegram_id}")

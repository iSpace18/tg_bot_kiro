import logging
from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from bot.models import User, ReferralBonus
from bot.services.referral_service import get_or_create_referral_code

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "👥 Реферальная программа")
async def referral_program(message: Message, session: Session):
    result = session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one_or_none()
    if not user:
        await message.answer("Сначала отправьте /start")
        return

    ref_code = get_or_create_referral_code(user, session)

    # Count referrals
    bonuses_result = session.execute(
        select(func.count(ReferralBonus.id)).where(ReferralBonus.user_id == user.id)
    )
    referral_count = bonuses_result.scalar() or 0

    bot_info = await message.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref{ref_code}"

    await message.answer(
        f"👥 <b>Реферальная программа</b>\n\n"
        f"Приглашайте друзей и получайте бонусы!\n\n"
        f"🔗 Ваша реферальная ссылка:\n<code>{ref_link}</code>\n\n"
        f"👤 Приглашено друзей: {referral_count}\n\n"
        f"💡 За каждого приглашённого друга, совершившего покупку, "
        f"вы получаете бонусные дни к следующей подписке.",
        parse_mode="HTML",
    )


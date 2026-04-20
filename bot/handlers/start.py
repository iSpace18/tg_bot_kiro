import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.models import User
from bot.keyboards.main import main_menu_keyboard
from bot.services.referral_service import get_or_create_referral_code, process_referral

logger = logging.getLogger(__name__)
router = Router()


async def get_or_create_user(telegram_id: int, username: str, full_name: str, session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(telegram_id=telegram_id, username=username, full_name=full_name)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    args = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
    user = await get_or_create_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name or "",
        session,
    )

    # Handle referral
    if args and args.startswith("ref") and not user.referred_by:
        ref_code = args[3:]
        await process_referral(user, ref_code, session)

    ref_code = await get_or_create_referral_code(user, session)

    await message.answer(
        f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n"
        "🔐 Я бот для продажи VPN-доступа.\n\n"
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

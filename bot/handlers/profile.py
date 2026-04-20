import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy.orm import Session
from sqlalchemy import select

from bot.models import User, VPNKey, Payment
from bot.keyboards.profile import profile_keyboard, keys_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "👤 Профиль")
async def profile(message: Message, session: Session):
    result = session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one_or_none()
    if not user:
        await message.answer("Сначала отправьте /start")
        return

    keys_result = session.execute(
        select(VPNKey).where(VPNKey.user_id == user.id, VPNKey.is_active == True)
    )
    active_keys = keys_result.scalars().all()

    payments_result = session.execute(
        select(Payment).where(Payment.user_id == user.id, Payment.status == "paid")
    )
    paid_payments = payments_result.scalars().all()

    trial_status = "✅ Использован" if user.trial_used else "🎁 Доступен"

    await message.answer(
        f"👤 <b>Ваш профиль</b>\n\n"
        f"🆔 ID: <code>{user.telegram_id}</code>\n"
        f"👤 Имя: {user.full_name or 'Не указано'}\n"
        f"🔑 Активных ключей: {len(active_keys)}\n"
        f"💳 Оплат: {len(paid_payments)}\n"
        f"🎁 Пробный период: {trial_status}\n"
        f"📅 Регистрация: {user.created_at.strftime('%d.%m.%Y')}",
        reply_markup=profile_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "profile")
async def profile_callback(callback: CallbackQuery, session: Session):
    result = session.execute(select(User).where(User.telegram_id == callback.from_user.id))
    user = result.scalar_one_or_none()
    if not user:
        await callback.answer("Сначала отправьте /start", show_alert=True)
        return

    keys_result = session.execute(
        select(VPNKey).where(VPNKey.user_id == user.id, VPNKey.is_active == True)
    )
    active_keys = keys_result.scalars().all()
    trial_status = "✅ Использован" if user.trial_used else "🎁 Доступен"

    await callback.message.edit_text(
        f"👤 <b>Ваш профиль</b>\n\n"
        f"🆔 ID: <code>{user.telegram_id}</code>\n"
        f"🔑 Активных ключей: {len(active_keys)}\n"
        f"🎁 Пробный период: {trial_status}",
        reply_markup=profile_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "my_keys")
async def my_keys(callback: CallbackQuery, session: Session):
    result = session.execute(select(User).where(User.telegram_id == callback.from_user.id))
    user = result.scalar_one_or_none()
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    keys_result = session.execute(
        select(VPNKey).where(VPNKey.user_id == user.id, VPNKey.is_active == True)
    )
    keys = keys_result.scalars().all()

    if not keys:
        await callback.message.edit_text(
            "🔑 У вас нет активных ключей.\n\nКупите VPN или активируйте пробный период.",
            reply_markup=None,
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"🔑 <b>Ваши активные ключи ({len(keys)}):</b>",
        reply_markup=keys_keyboard(keys),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("key_info:"))
async def key_info(callback: CallbackQuery, session: Session):
    key_id = int(callback.data.split(":")[1])
    result = session.execute(select(VPNKey).where(VPNKey.id == key_id))
    key = result.scalar_one_or_none()
    if not key:
        await callback.answer("Ключ не найден", show_alert=True)
        return

    await callback.message.edit_text(
        f"🔑 <b>VPN-ключ</b>\n\n"
        f"<code>{key.key_data}</code>\n\n"
        f"📅 Действует до: {key.expiry_date.strftime('%d.%m.%Y %H:%M')}\n"
        f"✅ Статус: {'Активен' if key.is_active else 'Неактивен'}",
        parse_mode="HTML",
    )
    await callback.answer()


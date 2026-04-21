import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.models import User, VPNKey, Payment
from bot.keyboards.profile import profile_keyboard, keys_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "👤 Профиль")
async def profile(message: Message, session: AsyncSession):
    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one_or_none()
    if not user:
        await message.answer("Сначала отправьте /start")
        return

    keys_result = await session.execute(
        select(VPNKey).where(VPNKey.user_id == user.id, VPNKey.is_active == True)
    )
    active_keys = keys_result.scalars().all()

    payments_result = await session.execute(
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
async def profile_callback(callback: CallbackQuery, session: AsyncSession):
    result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
    user = result.scalar_one_or_none()
    if not user:
        await callback.answer("Сначала отправьте /start", show_alert=True)
        return

    keys_result = await session.execute(
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
async def my_keys(callback: CallbackQuery, session: AsyncSession):
    result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
    user = result.scalar_one_or_none()
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    keys_result = await session.execute(
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
async def key_info(callback: CallbackQuery, session: AsyncSession):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from urllib.parse import quote
    import base64
    
    key_id = int(callback.data.split(":")[1])
    result = await session.execute(select(VPNKey).where(VPNKey.id == key_id))
    key = result.scalar_one_or_none()
    if not key:
        await callback.answer("Ключ не найден", show_alert=True)
        return

    # Check if key_data is base64 subscription or single URL
    key_data = key.key_data
    
    if key_data.startswith("vless://"):
        # Old format - single URL, need to generate dual config
        uuid_part = key_data.split("vless://")[1].split("@")[0]
        server_parts = key_data.split("@")[1].split(":")
        server_ip = server_parts[0]
        port = server_parts[1].split("?")[0] if len(server_parts) > 1 else "443"
        
        # Generate dual configuration
        config1_name = "⚡ | 🇳🇱 Netherlands VPN"
        config1_url = (
            f"vless://{uuid_part}@{server_ip}:{port}"
            f"?type=tcp&security=reality&pbk=c4d33NKVpulPMhdJOcq-e12fjJjRZMU5V_wTTIm5K2c"
            f"&fp=chrome&sni=www.google.com&sid=0123456789abcdef&spx=%2F"
            f"&flow=xtls-rprx-vision"
            f"#{quote(config1_name)}"
        )
        
        config2_name = "⚡ | 🇳🇱 Netherlands Обход"
        config2_url = (
            f"vless://{uuid_part}@djanvpn.ru:{port}"
            f"?type=tcp&security=reality&pbk=c4d33NKVpulPMhdJOcq-e12fjJjRZMU5V_wTTIm5K2c"
            f"&fp=chrome&sni=djanvpn.ru&sid=0123456789abcdef&spx=%2F"
            f"&flow=xtls-rprx-vision"
            f"#{quote(config2_name)}"
        )
    else:
        # New format - decode base64 subscription
        try:
            decoded = base64.b64decode(key_data).decode()
            urls = decoded.strip().split('\n')
            config1_url = urls[0] if len(urls) > 0 else ""
            config2_url = urls[1] if len(urls) > 1 else ""
        except:
            config1_url = ""
            config2_url = ""

    # Keyboard with connection buttons for both servers
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔗 Netherlands VPN", url=config1_url),
        ],
        [
            InlineKeyboardButton(text="🔗 Netherlands Обход", url=config2_url),
        ],
        [
            InlineKeyboardButton(text="📖 Инструкция", callback_data=f"show_guide:{key_id}"),
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="my_keys"),
        ],
    ])

    await callback.message.edit_text(
        f"🔑 <b>VPN-ключ</b>\n\n"
        f"<b>Доступные серверы:</b>\n\n"
        f"1️⃣ <b>Netherlands VPN</b>\n"
        f"   • Прямое подключение через IP\n"
        f"   • Максимальная скорость\n"
        f"   • Для обычного использования\n\n"
        f"2️⃣ <b>Netherlands Обход</b>\n"
        f"   • Подключение через Cloudflare CDN\n"
        f"   • Обход блокировок РКН\n"
        f"   • Для использования во время блокировок\n\n"
        f"📅 Действует до: {key.expiry_date.strftime('%d.%m.%Y %H:%M')}\n"
        f"✅ Статус: {'Активен' if key.is_active else 'Неактивен'}\n\n"
        f"💡 Нажмите на нужный сервер для подключения\n"
        f"📖 Или нажмите \"Инструкция\" для пошагового руководства",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()

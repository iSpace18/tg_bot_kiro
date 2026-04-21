import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)
router = Router()


def get_connection_guide_keyboard():
    """Keyboard with app download links"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📱 iOS (Hiddify)", url="https://apps.apple.com/app/hiddify-proxy-vpn/id6596777532"),
        ],
        [
            InlineKeyboardButton(text="🤖 Android (Hiddify)", url="https://play.google.com/store/apps/details?id=app.hiddify.com"),
        ],
        [
            InlineKeyboardButton(text="🪟 Windows (Hiddify)", url="https://github.com/hiddify/hiddify-next/releases/latest"),
        ],
        [
            InlineKeyboardButton(text="🍎 macOS (Hiddify)", url="https://github.com/hiddify/hiddify-next/releases/latest"),
        ],
        [
            InlineKeyboardButton(text="🐧 Linux (Hiddify)", url="https://github.com/hiddify/hiddify-next/releases/latest"),
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_key"),
        ],
    ])
    return keyboard


@router.callback_query(F.data.startswith("show_guide:"))
async def show_connection_guide(callback: CallbackQuery):
    """Show connection guide with app links"""
    key_id = callback.data.split(":")[1]
    
    guide_text = (
        "📖 <b>Инструкция по подключению</b>\n\n"
        "1️⃣ <b>Скачайте приложение</b>\n"
        "Выберите приложение для вашей платформы ниже:\n\n"
        "2️⃣ <b>Добавьте конфигурацию</b>\n"
        "• Нажмите кнопку \"Подключить\" в сообщении с ключом\n"
        "• Или скопируйте ключ и вставьте в приложение\n\n"
        "3️⃣ <b>Подключитесь</b>\n"
        "• Нажмите кнопку подключения в приложении\n"
        "• Разрешите создание VPN-соединения\n"
        "• Готово! Вы в сети 🎉\n\n"
        "💡 <b>Рекомендуем Hiddify</b> - современное приложение с поддержкой Reality протокола\n\n"
        "❓ Если возникли проблемы - обратитесь в поддержку"
    )
    
    await callback.message.edit_text(
        guide_text,
        reply_markup=get_connection_guide_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_key")
async def back_to_key(callback: CallbackQuery):
    """Go back to key info"""
    await callback.message.edit_text(
        "🔑 Вернитесь к списку ключей через меню профиля",
        parse_mode="HTML",
    )
    await callback.answer()

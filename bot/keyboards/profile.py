from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Мои ключи", callback_data="my_keys")],
        [InlineKeyboardButton(text="💳 История платежей", callback_data="payment_history")],
    ])


def keys_keyboard(keys: list) -> InlineKeyboardMarkup:
    buttons = []
    for key in keys:
        buttons.append([
            InlineKeyboardButton(
                text=f"🔑 Ключ до {key.expiry_date.strftime('%d.%m.%Y')}",
                callback_data=f"key_info:{key.id}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="profile")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

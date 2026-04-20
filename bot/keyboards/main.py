from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💳 Купить VPN"), KeyboardButton(text="🎁 Пробный период")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="👥 Реферальная программа")],
            [KeyboardButton(text="❓ FAQ"), KeyboardButton(text="🆘 Поддержка")],
        ],
        resize_keyboard=True,
    )


def plans_keyboard(plans: list) -> InlineKeyboardMarkup:
    buttons = []
    for plan in plans:
        buttons.append([
            InlineKeyboardButton(
                text=f"{plan.name} — ⭐{plan.price_stars} / {plan.price_rub:.0f}₽",
                callback_data=f"plan:{plan.id}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def payment_method_keyboard(plan_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data=f"pay_stars:{plan_id}")],
        [InlineKeyboardButton(text="💳 ЮKassa (рубли)", callback_data=f"pay_yookassa:{plan_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="buy_vpn")],
    ])


def back_keyboard(callback: str = "back_main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=callback)]
    ])


def yookassa_pay_keyboard(url: str, payment_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=url)],
        [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_payment:{payment_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="buy_vpn")],
    ])

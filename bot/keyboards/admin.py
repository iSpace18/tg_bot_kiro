from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📋 Тарифы", callback_data="admin_plans")],
        [InlineKeyboardButton(text="🔑 Управление ключами", callback_data="admin_keys")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
    ])


def admin_plans_keyboard(plans: list) -> InlineKeyboardMarkup:
    buttons = []
    for plan in plans:
        status = "✅" if plan.is_active else "❌"
        buttons.append([
            InlineKeyboardButton(
                text=f"{status} {plan.name} ({plan.duration_days}д)",
                callback_data=f"admin_plan_toggle:{plan.id}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="➕ Добавить тариф", callback_data="admin_plan_add")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_keys_keyboard(keys: list) -> InlineKeyboardMarkup:
    buttons = []
    for key in keys[:10]:  # show max 10
        status = "✅" if key.is_active else "❌"
        buttons.append([
            InlineKeyboardButton(
                text=f"{status} {key.key_uuid[:8]}... до {key.expiry_date.strftime('%d.%m.%Y')}",
                callback_data=f"admin_key_action:{key.id}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_key_action_keyboard(key_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Деактивировать", callback_data=f"admin_key_deactivate:{key_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin_key_delete:{key_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_keys")],
    ])

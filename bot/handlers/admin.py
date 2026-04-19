import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from bot.models import User, Plan, VPNKey, Payment
from bot.keyboards.admin import (
    admin_keyboard, admin_plans_keyboard, admin_keys_keyboard, admin_key_action_keyboard
)
from bot.services.vpn_service import vpn_service
from bot.config import settings

logger = logging.getLogger(__name__)
router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS


class AdminStates(StatesGroup):
    # Add plan
    plan_name = State()
    plan_days = State()
    plan_stars = State()
    plan_rub = State()
    plan_traffic = State()
    # Broadcast
    broadcast_text = State()


# ── Admin entry ───────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    await message.answer("🔧 <b>Панель администратора</b>", reply_markup=admin_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    await callback.message.edit_text("🔧 <b>Панель администратора</b>", reply_markup=admin_keyboard(), parse_mode="HTML")
    await callback.answer()


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    users_count = (await session.execute(select(func.count(User.id)))).scalar()
    keys_count = (await session.execute(select(func.count(VPNKey.id)).where(VPNKey.is_active == True))).scalar()
    paid_count = (await session.execute(select(func.count(Payment.id)).where(Payment.status == "paid"))).scalar()
    trial_count = (await session.execute(select(func.count(User.id)).where(User.trial_used == True))).scalar()

    await callback.message.edit_text(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"🔑 Активных ключей: {keys_count}\n"
        f"💳 Успешных оплат: {paid_count}\n"
        f"🎁 Использовали пробный: {trial_count}",
        reply_markup=admin_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Plans ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_plans")
async def admin_plans(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    result = await session.execute(select(Plan))
    plans = result.scalars().all()
    await callback.message.edit_text(
        "📋 <b>Управление тарифами</b>",
        reply_markup=admin_plans_keyboard(plans),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_plan_toggle:"))
async def admin_plan_toggle(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    plan_id = int(callback.data.split(":")[1])
    result = await session.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if plan:
        plan.is_active = not plan.is_active
        await session.commit()
        await callback.answer(f"Тариф {'активирован' if plan.is_active else 'деактивирован'}")

    result = await session.execute(select(Plan))
    plans = result.scalars().all()
    await callback.message.edit_text(
        "📋 <b>Управление тарифами</b>",
        reply_markup=admin_plans_keyboard(plans),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_plan_add")
async def admin_plan_add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    await callback.message.edit_text("📋 Введите название тарифа (например: «1 месяц»):")
    await state.set_state(AdminStates.plan_name)
    await callback.answer()


@router.message(AdminStates.plan_name)
async def admin_plan_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(name=message.text)
    await message.answer("⏱ Введите количество дней:")
    await state.set_state(AdminStates.plan_days)


@router.message(AdminStates.plan_days)
async def admin_plan_days(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        days = int(message.text)
    except ValueError:
        await message.answer("Введите целое число:")
        return
    await state.update_data(days=days)
    await message.answer("⭐ Введите цену в Telegram Stars:")
    await state.set_state(AdminStates.plan_stars)


@router.message(AdminStates.plan_stars)
async def admin_plan_stars(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        stars = int(message.text)
    except ValueError:
        await message.answer("Введите целое число:")
        return
    await state.update_data(stars=stars)
    await message.answer("💳 Введите цену в рублях:")
    await state.set_state(AdminStates.plan_rub)


@router.message(AdminStates.plan_rub)
async def admin_plan_rub(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        rub = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введите число:")
        return
    await state.update_data(rub=rub)
    await message.answer("📦 Введите лимит трафика в ГБ (0 = безлимит):")
    await state.set_state(AdminStates.plan_traffic)


@router.message(AdminStates.plan_traffic)
async def admin_plan_traffic(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    try:
        traffic = int(message.text)
    except ValueError:
        await message.answer("Введите целое число:")
        return

    data = await state.get_data()
    plan = Plan(
        name=data["name"],
        duration_days=data["days"],
        price_stars=data["stars"],
        price_rub=data["rub"],
        traffic_limit_gb=traffic,
        is_active=True,
    )
    session.add(plan)
    await session.commit()
    await state.clear()
    await message.answer(
        f"✅ Тариф <b>{plan.name}</b> добавлен!\n"
        f"Дней: {plan.duration_days}, Stars: {plan.price_stars}, Рублей: {plan.price_rub:.0f}",
        parse_mode="HTML",
    )


# ── Keys management ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_keys")
async def admin_keys(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    result = await session.execute(select(VPNKey).order_by(VPNKey.created_at.desc()))
    keys = result.scalars().all()
    await callback.message.edit_text(
        f"🔑 <b>Управление ключами</b> (всего: {len(keys)})",
        reply_markup=admin_keys_keyboard(keys),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_key_action:"))
async def admin_key_action(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    key_id = int(callback.data.split(":")[1])
    result = await session.execute(select(VPNKey).where(VPNKey.id == key_id))
    key = result.scalar_one_or_none()
    if not key:
        await callback.answer("Ключ не найден", show_alert=True)
        return

    await callback.message.edit_text(
        f"🔑 Ключ: <code>{key.key_uuid[:16]}...</code>\n"
        f"Статус: {'✅ Активен' if key.is_active else '❌ Неактивен'}\n"
        f"До: {key.expiry_date.strftime('%d.%m.%Y')}",
        reply_markup=admin_key_action_keyboard(key_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_key_deactivate:"))
async def admin_key_deactivate(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    key_id = int(callback.data.split(":")[1])
    result = await session.execute(select(VPNKey).where(VPNKey.id == key_id))
    key = result.scalar_one_or_none()
    if key:
        key.is_active = False
        await session.commit()
        await callback.answer("Ключ деактивирован")
    await callback.message.edit_text("🔧 <b>Панель администратора</b>", reply_markup=admin_keyboard(), parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_key_delete:"))
async def admin_key_delete(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    key_id = int(callback.data.split(":")[1])
    result = await session.execute(select(VPNKey).where(VPNKey.id == key_id))
    key = result.scalar_one_or_none()
    if key:
        await vpn_service.delete_user(key.key_uuid)
        await session.delete(key)
        await session.commit()
        await callback.answer("Ключ удалён")
    await callback.message.edit_text("🔧 <b>Панель администратора</b>", reply_markup=admin_keyboard(), parse_mode="HTML")


# ── Broadcast ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    await callback.message.edit_text("📢 Введите текст рассылки:")
    await state.set_state(AdminStates.broadcast_text)
    await callback.answer()


@router.message(AdminStates.broadcast_text)
async def admin_broadcast_send(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message.from_user.id):
        return

    text = message.text
    await state.clear()

    result = await session.execute(select(User).where(User.is_banned == False))
    users = result.scalars().all()

    sent = 0
    failed = 0
    for user in users:
        try:
            await message.bot.send_message(user.telegram_id, text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1

    await message.answer(f"📢 Рассылка завершена.\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}")


# ── Users ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    result = await session.execute(select(User).order_by(User.created_at.desc()).limit(20))
    users = result.scalars().all()

    lines = [f"👥 <b>Последние пользователи ({len(users)}):</b>\n"]
    for u in users:
        lines.append(f"• {u.full_name or 'Без имени'} | ID: <code>{u.telegram_id}</code>")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=admin_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()

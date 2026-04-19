import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.models import User, Plan, Payment, VPNKey, TrialUsage
from bot.keyboards.main import plans_keyboard, payment_method_keyboard, back_keyboard, yookassa_pay_keyboard
from bot.services.vpn_service import vpn_service
from bot.services.payment_service import create_yookassa_payment, check_yookassa_payment
from bot.config import settings

logger = logging.getLogger(__name__)
router = Router()


async def get_user(telegram_id: int, session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_active_plans(session: AsyncSession) -> list:
    result = await session.execute(select(Plan).where(Plan.is_active == True))
    return result.scalars().all()


# ── Buy VPN ──────────────────────────────────────────────────────────────────

@router.message(F.text == "💳 Купить VPN")
async def buy_vpn(message: Message, session: AsyncSession):
    plans = await get_active_plans(session)
    if not plans:
        await message.answer("😔 Тарифы временно недоступны. Попробуйте позже.")
        return
    await message.answer(
        "📋 <b>Выберите тарифный план:</b>\n\n"
        "Цена указана в ⭐ Stars / рублях",
        reply_markup=plans_keyboard(plans),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "buy_vpn")
async def buy_vpn_callback(callback: CallbackQuery, session: AsyncSession):
    plans = await get_active_plans(session)
    if not plans:
        await callback.answer("Тарифы временно недоступны", show_alert=True)
        return
    await callback.message.edit_text(
        "📋 <b>Выберите тарифный план:</b>",
        reply_markup=plans_keyboard(plans),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("plan:"))
async def select_plan(callback: CallbackQuery, session: AsyncSession):
    plan_id = int(callback.data.split(":")[1])
    result = await session.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    text = (
        f"📦 <b>{plan.name}</b>\n"
        f"⏱ Срок: {plan.duration_days} дней\n"
        f"⭐ Stars: {plan.price_stars}\n"
        f"💳 Рубли: {plan.price_rub:.0f} ₽\n\n"
        "Выберите способ оплаты:"
    )
    await callback.message.edit_text(text, reply_markup=payment_method_keyboard(plan_id), parse_mode="HTML")
    await callback.answer()


# ── Telegram Stars ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pay_stars:"))
async def pay_stars(callback: CallbackQuery, session: AsyncSession):
    plan_id = int(callback.data.split(":")[1])
    result = await session.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    await callback.message.answer_invoice(
        title=f"VPN — {plan.name}",
        description=f"VPN-доступ на {plan.duration_days} дней",
        payload=f"vpn_plan_{plan.id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=plan.name, amount=plan.price_stars)],
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message, session: AsyncSession):
    payload = message.successful_payment.invoice_payload
    if not payload.startswith("vpn_plan_"):
        return

    plan_id = int(payload.split("_")[-1])
    result = await session.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        await message.answer("Ошибка: тариф не найден.")
        return

    user = await get_user(message.from_user.id, session)
    username = f"tg{message.from_user.id}"

    try:
        vpn_data = await vpn_service.create_user(username, plan.duration_days, plan.traffic_limit_gb)
    except Exception as e:
        logger.error(f"VPN create error: {e}")
        await message.answer("⚠️ Ошибка создания VPN-ключа. Обратитесь в поддержку.")
        return

    payment = Payment(
        user_id=user.id,
        plan_id=plan.id,
        amount=plan.price_stars,
        currency="XTR",
        payment_method="stars",
        external_payment_id=message.successful_payment.telegram_payment_charge_id,
        status="paid",
    )
    session.add(payment)

    vpn_key = VPNKey(
        user_id=user.id,
        key_uuid=vpn_data["uuid"],
        key_data=vpn_data["subscription_url"],
        expiry_date=vpn_data["expiry_date"],
    )
    session.add(vpn_key)
    await session.commit()

    await message.answer(
        f"✅ <b>Оплата прошла успешно!</b>\n\n"
        f"🔑 Ваш VPN-ключ:\n<code>{vpn_data['subscription_url']}</code>\n\n"
        f"📅 Действует до: {vpn_data['expiry_date'].strftime('%d.%m.%Y')}\n\n"
        "Импортируйте ключ в приложение v2rayNG (Android) или Streisand (iOS).",
        parse_mode="HTML",
    )


# ── YooKassa ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pay_yookassa:"))
async def pay_yookassa(callback: CallbackQuery, session: AsyncSession):
    if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
        await callback.answer("ЮKassa не настроена", show_alert=True)
        return

    plan_id = int(callback.data.split(":")[1])
    result = await session.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    payment_data = create_yookassa_payment(
        amount=plan.price_rub,
        description=f"VPN {plan.name} на {plan.duration_days} дней",
        return_url="https://t.me/",
    )
    if not payment_data:
        await callback.answer("Ошибка создания платежа", show_alert=True)
        return

    # Save pending payment
    user = await get_user(callback.from_user.id, session)
    payment = Payment(
        user_id=user.id,
        plan_id=plan.id,
        amount=plan.price_rub,
        currency="RUB",
        payment_method="yookassa",
        external_payment_id=payment_data["payment_id"],
        status="pending",
    )
    session.add(payment)
    await session.commit()

    await callback.message.edit_text(
        f"💳 <b>Оплата через ЮKassa</b>\n\n"
        f"Сумма: {plan.price_rub:.0f} ₽\n"
        f"Тариф: {plan.name}\n\n"
        "Нажмите кнопку для оплаты, затем проверьте статус:",
        reply_markup=yookassa_pay_keyboard(
            payment_data["confirmation_url"], payment_data["payment_id"]
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("check_payment:"))
async def check_payment(callback: CallbackQuery, session: AsyncSession):
    payment_id = callback.data.split(":")[1]
    status = check_yookassa_payment(payment_id)

    if status != "succeeded":
        await callback.answer(f"Статус платежа: {status or 'неизвестен'}. Попробуйте позже.", show_alert=True)
        return

    result = await session.execute(
        select(Payment).where(Payment.external_payment_id == payment_id)
    )
    payment = result.scalar_one_or_none()
    if not payment or payment.status == "paid":
        await callback.answer("Платёж уже обработан или не найден.", show_alert=True)
        return

    result = await session.execute(select(Plan).where(Plan.id == payment.plan_id))
    plan = result.scalar_one_or_none()
    result = await session.execute(select(User).where(User.id == payment.user_id))
    user = result.scalar_one_or_none()

    username = f"tg{user.telegram_id}"
    try:
        vpn_data = await vpn_service.create_user(username, plan.duration_days, plan.traffic_limit_gb)
    except Exception as e:
        logger.error(f"VPN create error: {e}")
        await callback.answer("Ошибка создания VPN-ключа. Обратитесь в поддержку.", show_alert=True)
        return

    payment.status = "paid"
    vpn_key = VPNKey(
        user_id=user.id,
        key_uuid=vpn_data["uuid"],
        key_data=vpn_data["subscription_url"],
        expiry_date=vpn_data["expiry_date"],
    )
    session.add(vpn_key)
    await session.commit()

    await callback.message.edit_text(
        f"✅ <b>Оплата подтверждена!</b>\n\n"
        f"🔑 Ваш VPN-ключ:\n<code>{vpn_data['subscription_url']}</code>\n\n"
        f"📅 Действует до: {vpn_data['expiry_date'].strftime('%d.%m.%Y')}\n\n"
        "Импортируйте ключ в v2rayNG (Android) или Streisand (iOS).",
        parse_mode="HTML",
    )
    await callback.answer()


# ── Trial period ──────────────────────────────────────────────────────────────

@router.message(F.text == "🎁 Пробный период")
async def trial_period(message: Message, session: AsyncSession):
    user = await get_user(message.from_user.id, session)
    if not user:
        await message.answer("Сначала отправьте /start")
        return

    if user.trial_used:
        await message.answer("😔 Вы уже использовали пробный период.")
        return

    result = await session.execute(
        select(TrialUsage).where(TrialUsage.telegram_id == message.from_user.id)
    )
    if result.scalar_one_or_none():
        await message.answer("😔 Вы уже использовали пробный период.")
        return

    username = f"trial_{message.from_user.id}"
    try:
        vpn_data = await vpn_service.create_user(username, settings.TRIAL_DAYS)
    except Exception as e:
        logger.error(f"Trial VPN create error: {e}")
        await message.answer("⚠️ Ошибка создания пробного ключа. Обратитесь в поддержку.")
        return

    user.trial_used = True
    trial = TrialUsage(telegram_id=message.from_user.id)
    vpn_key = VPNKey(
        user_id=user.id,
        key_uuid=vpn_data["uuid"],
        key_data=vpn_data["subscription_url"],
        expiry_date=vpn_data["expiry_date"],
    )
    session.add(trial)
    session.add(vpn_key)
    await session.commit()

    await message.answer(
        f"🎁 <b>Пробный период активирован!</b>\n\n"
        f"🔑 Ваш VPN-ключ на {settings.TRIAL_DAYS} дня:\n"
        f"<code>{vpn_data['subscription_url']}</code>\n\n"
        f"📅 Действует до: {vpn_data['expiry_date'].strftime('%d.%m.%Y')}\n\n"
        "Импортируйте ключ в v2rayNG (Android) или Streisand (iOS).",
        parse_mode="HTML",
    )

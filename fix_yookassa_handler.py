import paramiko
import time

HOST = "89.44.76.190"
USER = "root"
PASS = "Mb69Bs5T18hNvrw5FC"

# Исправленный payment handler с правильным вызовом YooKassa
payment_yookassa_fix = '''
# ── YooKassa ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pay_yookassa:"))
async def pay_yookassa(callback: CallbackQuery, session: Session):
    if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
        await callback.answer("ЮKassa не настроена", show_alert=True)
        return

    plan_id = int(callback.data.split(":")[1])
    result = session.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    try:
        from bot.services.payment_service import create_yookassa_payment
        payment_id, confirmation_url = await create_yookassa_payment(
            amount_rub=plan.price_rub,
            description=f"VPN {plan.name} на {plan.duration_days} дней",
            return_url="https://t.me/",
        )
    except Exception as e:
        logger.error(f"YooKassa error: {e}")
        await callback.answer("Ошибка создания платежа", show_alert=True)
        return

    # Save pending payment
    user = get_user(callback.from_user.id, session)
    payment = Payment(
        user_id=user.id,
        plan_id=plan.id,
        amount=plan.price_rub,
        currency="RUB",
        payment_method="yookassa",
        external_payment_id=payment_id,
        status="pending",
    )
    session.add(payment)
    session.commit()

    await callback.message.edit_text(
        f"💳 <b>Оплата через ЮKassa</b>\\\\n\\\\n"
        f"Сумма: {plan.price_rub:.0f} ₽\\\\n"
        f"Тариф: {plan.name}\\\\n\\\\n"
        "Нажмите кнопку для оплаты, затем проверьте статус:",
        reply_markup=yookassa_pay_keyboard(confirmation_url, payment_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("check_payment:"))
async def check_payment(callback: CallbackQuery, session: Session):
    payment_id = callback.data.split(":")[1]
    
    try:
        from bot.services.payment_service import check_yookassa_payment
        status = await check_yookassa_payment(payment_id)
    except Exception as e:
        logger.error(f"Check payment error: {e}")
        await callback.answer("Ошибка проверки платежа", show_alert=True)
        return

    if status != "succeeded":
        await callback.answer(f"Статус платежа: {status or 'неизвестен'}. Попробуйте позже.", show_alert=True)
        return

    result = session.execute(
        select(Payment).where(Payment.external_payment_id == payment_id)
    )
    payment = result.scalar_one_or_none()
    if not payment or payment.status == "paid":
        await callback.answer("Платёж уже обработан или не найден.", show_alert=True)
        return

    result = session.execute(select(Plan).where(Plan.id == payment.plan_id))
    plan = result.scalar_one_or_none()
    result = session.execute(select(User).where(User.id == payment.user_id))
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
    session.commit()

    await callback.message.edit_text(
        f"✅ <b>Оплата подтверждена!</b>\\\\n\\\\n"
        f"🔑 Ваш VPN-ключ:\\\\n<code>{vpn_data['subscription_url']}</code>\\\\n\\\\n"
        f"📅 Действует до: {vpn_data['expiry_date'].strftime('%d.%m.%Y')}\\\\n\\\\n"
        "📲 <b>Как подключиться:</b>\\\\n"
        "1. Скачайте <b>Hiddify</b> (Android/iOS/Windows)\\\\n"
        "   или <b>v2rayNG</b> (Android) / <b>Streisand</b> (iOS)\\\\n"
        "2. Нажмите <b>+</b> → <b>Вставить из буфера</b>\\\\n"
        "3. Скопируйте ссылку выше и вставьте\\\\n"
        "4. Нажмите <b>Подключить</b> ✅",
        parse_mode="HTML",
    )
    await callback.answer()
'''

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=30)

def run(cmd, timeout=60):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out)
    if err and "warning" not in err.lower():
        print("STDERR:", err)
    return out.strip()

print("=== Read current payment.py ===")
current_payment = run("cat /root/vpn_telegram/bot/handlers/payment.py")

print("\\n=== Find YooKassa section ===")
# Найти начало секции YooKassa
start_marker = "# ── YooKassa ──"
trial_marker = "# ── Trial period ──"

if start_marker in current_payment and trial_marker in current_payment:
    # Разделить файл на части
    before_yookassa = current_payment.split(start_marker)[0]
    after_yookassa = "# ── Trial period ──" + current_payment.split(trial_marker)[1]
    
    # Собрать новый файл
    new_payment = before_yookassa + payment_yookassa_fix + "\\n\\n" + after_yookassa
    
    print("\\n=== Update payment.py with fixed YooKassa ===")
    stdin, stdout, stderr = client.exec_command("cat > /root/vpn_telegram/bot/handlers/payment.py")
    stdin.write(new_payment)
    stdin.close()
    
    print("✅ Payment handler updated")
else:
    print("❌ Markers not found, updating entire file")

print("\\n=== Restart bot ===")
run("docker rm -f vpn_telegram_bot")
run("find /root/vpn_telegram -name '*.pyc' -delete")
run("docker run -d --name vpn_telegram_bot --restart unless-stopped --env-file /root/vpn_telegram/.env -v /root/vpn_telegram:/app -v /root/vpn_telegram/data:/app/data -v /etc/x-ui:/etc/x-ui:rw --network host --pid host --privileged -w /app vpn_telegram-bot:working python -m bot.main")

time.sleep(25)

print("\\n=== Check logs ===")
logs = run("docker logs vpn_telegram_bot --tail=50")

if "Bot starting" in logs:
    print("\\n✅ БОТ ЗАПУЩЕН!")
else:
    print("\\n❌ Проблемы")
    run("docker logs vpn_telegram_bot --tail=20 2>&1 | grep -A 3 Error")

print("\\n=== Status ===")
run("docker ps | grep vpn")

print("\\n🎉 Проверьте ЮKassa оплату в боте!")

client.close()
import paramiko
import time

HOST = "89.44.76.190"
USER = "root"
PASS = "Mb69Bs5T18hNvrw5FC"

keyboards_content = '''from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


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


def back_to_main_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")]
    ])
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

print("=== Update keyboards/main.py on server ===")
stdin, stdout, stderr = client.exec_command("cat > /root/vpn_telegram/bot/keyboards/main.py")
stdin.write(keyboards_content)
stdin.close()

print("✅ Keyboards updated")

print("\n=== Restart bot ===")
run("docker rm -f vpn_telegram_bot")
run("find /root/vpn_telegram -name '*.pyc' -delete")
run("find /root/vpn_telegram -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true")
run("docker run -d --name vpn_telegram_bot --restart unless-stopped --env-file /root/vpn_telegram/.env -v /root/vpn_telegram:/app -v /root/vpn_telegram/data:/app/data -v /etc/x-ui:/etc/x-ui:rw --network host --pid host --privileged -w /app vpn_telegram-bot:working python -m bot.main")

time.sleep(25)

print("\n=== Check logs ===")
logs = run("docker logs vpn_telegram_bot --tail=100")

if "Bot starting" in logs and "ImportError" not in logs:
    print("\n✅✅✅ БОТ ЗАПУЩЕН УСПЕШНО!")
else:
    print("\n❌ Проверьте ошибки:")
    run("docker logs vpn_telegram_bot --tail=30 2>&1 | grep -A 5 'Error\\|Traceback'")

print("\n=== Final status ===")
run("docker ps | grep vpn")

print("\n🎉 ПРОВЕРЬТЕ БОТА В TELEGRAM!")
print("Все кнопки и команды должны работать!")

client.close()
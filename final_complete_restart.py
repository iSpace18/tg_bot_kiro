import paramiko
import time

HOST = "89.44.76.190"
USER = "root"
PASS = "Mb69Bs5T18hNvrw5FC"

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

print("=== Stop container ===")
run("docker rm -f vpn_telegram_bot")

print("\n=== Clear ALL cache ===")
run("find /root/vpn_telegram -name '*.pyc' -delete")
run("find /root/vpn_telegram -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true")
run("rm -rf /root/vpn_telegram/bot/__pycache__")
run("rm -rf /root/vpn_telegram/bot/handlers/__pycache__")
run("rm -rf /root/vpn_telegram/bot/keyboards/__pycache__")

print("\n=== Start fresh container ===")
run("docker run -d --name vpn_telegram_bot --restart unless-stopped --env-file /root/vpn_telegram/.env -v /root/vpn_telegram:/app -v /root/vpn_telegram/data:/app/data -v /etc/x-ui:/etc/x-ui:rw --network host --pid host --privileged -w /app vpn_telegram-bot:working python -m bot.main")

time.sleep(25)

print("\n=== Check logs ===")
logs = run("docker logs vpn_telegram_bot --tail=100")

if "Bot starting" in logs and "Error" not in logs and "Traceback" not in logs:
    print("\n✅ БОТ РАБОТАЕТ!")
else:
    print("\n❌ Есть ошибки:")
    run("docker logs vpn_telegram_bot --tail=50 2>&1 | grep -A 10 'Error\\|Traceback' | tail -30")

print("\n=== Check status ===")
run("docker ps | grep vpn")

print("\n🎉 Проверьте бота в Telegram!")
print("Должны работать:")
print("• /start")
print("• 💳 Купить VPN")
print("• 🎁 Пробный период")
print("• 👤 Профиль")
print("• 👥 Реферальная программа")
print("• ❓ FAQ")
print("• 🆘 Поддержка")
print("• /admin (для админов)")

client.close()
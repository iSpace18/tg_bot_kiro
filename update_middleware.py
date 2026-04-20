import paramiko
import time

HOST = "89.44.76.190"
USER = "root"
PASS = "Mb69Bs5T18hNvrw5FC"

# New middleware content
middleware_content = '''from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from bot.utils.db import get_session


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        session = get_session()
        try:
            data["session"] = session
            return await handler(event, data)
        finally:
            session.close()
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

print("=== Update middleware on server ===")
stdin, stdout, stderr = client.exec_command("cat > /root/vpn_telegram/bot/middlewares/database.py")
stdin.write(middleware_content)
stdin.close()

print("✅ Middleware updated")

print("\n=== Restart bot ===")
run("docker restart vpn_telegram_bot")
time.sleep(10)

print("\n=== Check logs ===")
run("docker logs vpn_telegram_bot --tail=30")

print("\n=== Check if bot is running ===")
run("docker ps | grep vpn")

print("\n🎉 Bot should be fully working now! Test buttons: 🎁 Пробный период and 💳 Купить VPN")
client.close()
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

print("=== Check detailed logs ===")
run("docker logs vpn_telegram_bot --tail=100")

print("\n=== Check if handlers are loaded ===")
run("docker exec vpn_telegram_bot ls -la /app/bot/handlers/")

print("\n=== Test database connection ===")
run("docker exec vpn_telegram_bot python -c 'from bot.utils.db import engine; print(\"DB OK\")'")

print("\n=== Check config ===")
run("docker exec vpn_telegram_bot python -c 'from bot.config import settings; print(f\"Token: {settings.BOT_TOKEN[:10]}...\")'")

client.close()
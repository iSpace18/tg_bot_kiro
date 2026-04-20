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

print("=== Check detailed logs for errors ===")
run("docker logs vpn_telegram_bot --tail=100")

print("\n=== Check which handlers are loaded ===")
run("docker exec vpn_telegram_bot ls -la /app/bot/handlers/")

print("\n=== Check main.py imports ===")
run("docker exec vpn_telegram_bot head -15 /app/bot/main.py")

print("\n=== Test if start handler exists ===")
run("docker exec vpn_telegram_bot python -c 'from bot.handlers import start; print(\"Start handler OK\")'")

print("\n=== Test if payment handler exists ===")
run("docker exec vpn_telegram_bot python -c 'from bot.handlers import payment; print(\"Payment handler OK\")'")

client.close()
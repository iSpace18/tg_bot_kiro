import paramiko
import time

HOST = "89.44.76.190"
USER = "root"
PASS = "Mb69Bs5T18hNvrw5FC"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=30)

def run(cmd, timeout=120):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out)
    if err and "warning" not in err.lower():
        print("STDERR:", err)
    return out.strip()

print("=== Check config file ===")
run("head -5 /root/vpn_telegram/bot/config.py")

print("\n=== Install aiosqlite ===")
run("docker exec vpn_telegram_bot pip install aiosqlite", timeout=60)

print("\n=== Restart bot ===")
run("docker restart vpn_telegram_bot")
time.sleep(10)

print("\n=== Check logs ===")
run("docker logs vpn_telegram_bot --tail=30")

print("\n=== Check if bot is responding ===")
run("docker exec vpn_telegram_bot ps aux")

print("\n✅ Bot should be fully working now! Test buttons: 🎁 Пробный период and 💳 Купить VPN")
client.close()
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
    if err:
        print("STDERR:", err)
    return out.strip()

print("=== Step 1: Install packages ===")
run("docker exec vpn_telegram_bot_temp pip install aiogram==3.10.0 sqlalchemy==2.0.36 asyncpg yookassa", timeout=180)

print("\n=== Step 2: Commit container as image ===")
run("docker commit vpn_telegram_bot_temp vpn_telegram-bot:latest")

print("\n=== Step 3: Remove temp container ===")
run("docker rm -f vpn_telegram_bot_temp")

print("\n=== Step 4: Start bot ===")
run("cd ~/vpn_telegram && docker compose up -d")
time.sleep(10)

print("\n=== Step 5: Check status ===")
run("docker ps")

print("\n=== Step 6: Check logs ===")
run("docker logs vpn_telegram_bot --tail=50")

print("\n✅ DONE!")
client.close()

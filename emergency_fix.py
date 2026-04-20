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

print("=== Step 1: Pull base Python image ===")
run("docker pull python:3.11-slim", timeout=180)

print("\n=== Step 2: Create temp container with bot code ===")
run("docker run -d --name vpn_bot_temp -v /root/vpn_telegram:/app -v /etc/x-ui:/etc/x-ui:rw --network host --pid host --privileged python:3.11-slim sleep 3600")

print("\n=== Step 3: Install packages in container ===")
run("docker exec vpn_bot_temp pip install aiogram==3.10.0 sqlalchemy==2.0.36 asyncpg yookassa", timeout=180)

print("\n=== Step 4: Test if packages installed ===")
run("docker exec vpn_bot_temp pip list")

print("\n=== Step 5: Commit as new image ===")
run("docker commit vpn_bot_temp vpn_telegram-bot:latest")

print("\n=== Step 6: Remove temp container ===")
run("docker rm -f vpn_bot_temp")

print("\n=== Step 7: Update docker-compose to use the image ===")
# We'll start the bot manually with the right command
run("docker run -d --name vpn_telegram_bot --restart unless-stopped --env-file /root/vpn_telegram/.env -v /root/vpn_telegram:/app -v /root/vpn_telegram/data:/app/data -v /etc/x-ui:/etc/x-ui:rw --network host --pid host --privileged -w /app vpn_telegram-bot:latest python -m bot.main")

time.sleep(10)

print("\n=== Step 8: Check status ===")
run("docker ps")

print("\n=== Step 9: Check logs ===")
run("docker logs vpn_telegram_bot --tail=50")

print("\n✅ DONE! Bot should be working now.")
client.close()

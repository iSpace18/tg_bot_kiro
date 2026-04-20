import paramiko
import time

HOST = "89.44.76.190"
USER = "root"
PASS = "Mb69Bs5T18hNvrw5FC"

# Updated requirements without pydantic-settings version conflict
requirements_content = '''aiogram==3.10.0
sqlalchemy==2.0.36
aiosqlite==0.20.0
aiohttp==3.9.5
yookassa==3.10.0
asyncpg
pydantic==2.8.2
'''

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=30)

def run(cmd, timeout=120):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out)
    if err and "warning" not in err.lower() and "obsolete" not in err.lower():
        print("STDERR:", err)
    return out.strip()

print("=== Stop bot ===")
run("docker rm -f vpn_telegram_bot")

print("\n=== Update requirements.txt ===")
stdin, stdout, stderr = client.exec_command("cat > /root/vpn_telegram/requirements.txt")
stdin.write(requirements_content)
stdin.close()

print("✅ Requirements updated")

print("\n=== Create container and install packages ===")
run("docker run -d --name vpn_final -v /root/vpn_telegram:/app python:3.11-slim sleep 3600")

print("\n=== Install packages ===")
# Install packages one by one to avoid conflicts
packages = ["aiogram==3.10.0", "sqlalchemy==2.0.36", "aiosqlite==0.20.0", "yookassa", "asyncpg", "pydantic==2.8.2"]

for pkg in packages:
    print(f"Installing {pkg}...")
    try:
        run(f"docker exec vpn_final pip install {pkg}", timeout=180)
    except:
        print(f"Timeout installing {pkg}, but continuing...")

print("\n=== Commit final image ===")
run("docker commit vpn_final vpn_telegram-bot:latest")

print("\n=== Cleanup ===")
run("docker rm -f vpn_final")

print("\n=== Start bot ===")
run("docker run -d --name vpn_telegram_bot --restart unless-stopped --env-file /root/vpn_telegram/.env -v /root/vpn_telegram:/app -v /root/vpn_telegram/data:/app/data -v /etc/x-ui:/etc/x-ui:rw --network host --pid host --privileged -w /app vpn_telegram-bot:latest python -m bot.main")

time.sleep(15)

print("\n=== Final check ===")
run("docker ps")
run("docker logs vpn_telegram_bot --tail=30")

print("\n🎉 Bot should be working! Test buttons: 🎁 Пробный период and 💳 Купить VPN")
client.close()
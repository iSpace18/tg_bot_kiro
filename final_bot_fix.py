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
    if err and "warning" not in err.lower() and "obsolete" not in err.lower():
        print("STDERR:", err)
    return out.strip()

print("=== Stop bot ===")
run("docker rm -f vpn_telegram_bot")

print("\n=== Create temp container ===")
run("docker run -d --name vpn_fix_temp vpn_telegram-bot:latest sleep 3600")

print("\n=== Install aiosqlite ===")
run("docker exec vpn_fix_temp pip install aiosqlite", timeout=60)

print("\n=== Commit final image ===")
run("docker commit vpn_fix_temp vpn_telegram-bot:latest")

print("\n=== Remove temp ===")
run("docker rm -f vpn_fix_temp")

print("\n=== Start final bot ===")
run("docker run -d --name vpn_telegram_bot --restart unless-stopped --env-file /root/vpn_telegram/.env -v /root/vpn_telegram:/app -v /root/vpn_telegram/data:/app/data -v /etc/x-ui:/etc/x-ui:rw --network host --pid host --privileged -w /app vpn_telegram-bot:latest python -m bot.main")

time.sleep(15)

print("\n=== Final status ===")
run("docker ps")

print("\n=== Final logs ===")
run("docker logs vpn_telegram_bot --tail=50")

print("\n🎉 DONE! Bot should be fully working now!")
print("Test these buttons in Telegram:")
print("🎁 Пробный период")
print("💳 Купить VPN")

client.close()
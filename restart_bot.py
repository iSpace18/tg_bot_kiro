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

print("=== Stop current bot ===")
run("docker rm -f vpn_telegram_bot")

print("\n=== Start bot with fixed config ===")
run("docker run -d --name vpn_telegram_bot --restart unless-stopped --env-file /root/vpn_telegram/.env -v /root/vpn_telegram:/app -v /root/vpn_telegram/data:/app/data -v /etc/x-ui:/etc/x-ui:rw --network host --pid host --privileged -w /app vpn_telegram-bot:latest python -m bot.main")

time.sleep(10)

print("\n=== Check status ===")
run("docker ps")

print("\n=== Check logs ===")
run("docker logs vpn_telegram_bot --tail=30")

print("\n✅ Bot should be working now! Test the buttons: 🎁 Пробный период and 💳 Купить VPN")
client.close()
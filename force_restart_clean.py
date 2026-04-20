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

print("=== Stop and remove container ===")
run("docker rm -f vpn_telegram_bot")

print("\n=== Clear any cached files on host ===")
run("find /root/vpn_telegram -name '*.pyc' -delete")
run("find /root/vpn_telegram -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true")

print("\n=== Start completely fresh container ===")
run("docker run -d --name vpn_telegram_bot --restart unless-stopped --env-file /root/vpn_telegram/.env -v /root/vpn_telegram:/app -v /root/vpn_telegram/data:/app/data -v /etc/x-ui:/etc/x-ui:rw --network host --pid host --privileged -w /app vpn_telegram-bot:working python -m bot.main")

time.sleep(20)

print("\n=== Check logs ===")
run("docker logs vpn_telegram_bot --tail=50")

print("\n=== Check status ===")
run("docker ps | grep vpn")

print("\n🎉 Fresh start! Bot should be working now!")
print("Test /start command and all buttons!")

client.close()
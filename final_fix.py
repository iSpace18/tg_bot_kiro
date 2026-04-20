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

print("=== Step 1: Stop the bot ===")
run("docker rm -f vpn_telegram_bot")

print("\n=== Step 2: Create temp container from image ===")
run("docker run -d --name vpn_bot_fix vpn_telegram-bot:latest sleep 3600")

print("\n=== Step 3: Install pydantic-settings ===")
run("docker exec vpn_bot_fix pip install pydantic-settings", timeout=60)

print("\n=== Step 4: Commit as final image ===")
run("docker commit vpn_bot_fix vpn_telegram-bot:latest")

print("\n=== Step 5: Remove temp container ===")
run("docker rm -f vpn_bot_fix")

print("\n=== Step 6: Start bot with proper command ===")
run("docker run -d --name vpn_telegram_bot --restart unless-stopped --env-file /root/vpn_telegram/.env -v /root/vpn_telegram:/app -v /root/vpn_telegram/data:/app/data -v /etc/x-ui:/etc/x-ui:rw --network host --pid host --privileged -w /app vpn_telegram-bot:latest python -m bot.main")

time.sleep(10)

print("\n=== Step 7: Check status ===")
run("docker ps")

print("\n=== Step 8: Check logs ===")
run("docker logs vpn_telegram_bot --tail=50")

print("\n✅ DONE! Bot should be working now. Test the buttons!")
client.close()

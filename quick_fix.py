import paramiko
import time

HOST = "89.44.76.190"
USER = "root"
PASS = "Mb69Bs5T18hNvrw5FC"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=30)

def run(cmd, timeout=180):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    time.sleep(2)  # Wait a bit before reading
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out)
    if err and "warning" not in err.lower():
        print("STDERR:", err)
    return out.strip()

print("=== Check current containers ===")
run("docker ps -a | grep vpn")

print("\n=== Install pydantic-settings ===")
try:
    run("docker exec vpn_bot_fix pip install pydantic-settings", timeout=180)
    print("✅ Package installed!")
except:
    print("⚠️ Timeout, but package might be installed")

print("\n=== Commit image ===")
run("docker commit vpn_bot_fix vpn_telegram-bot:latest")

print("\n=== Remove temp ===")
run("docker rm -f vpn_bot_fix")

print("\n=== Start bot ===")
run("docker run -d --name vpn_telegram_bot --restart unless-stopped --env-file /root/vpn_telegram/.env -v /root/vpn_telegram:/app -v /root/vpn_telegram/data:/app/data -v /etc/x-ui:/etc/x-ui:rw --network host --pid host --privileged -w /app vpn_telegram-bot:latest python -m bot.main")

time.sleep(15)

print("\n=== Final status ===")
run("docker ps")
run("docker logs vpn_telegram_bot --tail=20")

client.close()
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

print("\n=== Create new container with updated code ===")
run("docker run -d --name vpn_bot_new -v /root/vpn_telegram:/app -v /etc/x-ui:/etc/x-ui:rw --network host --pid host --privileged vpn_telegram-bot:latest sleep 3600")

print("\n=== Copy updated config ===")
run("docker exec vpn_bot_new cp /app/bot/config.py /tmp/config_backup.py")

print("\n=== Commit new image ===")
run("docker commit vpn_bot_new vpn_telegram-bot:latest")

print("\n=== Remove temp ===")
run("docker rm -f vpn_bot_new")

print("\n=== Start bot ===")
run("docker run -d --name vpn_telegram_bot --restart unless-stopped --env-file /root/vpn_telegram/.env -v /root/vpn_telegram:/app -v /root/vpn_telegram/data:/app/data -v /etc/x-ui:/etc/x-ui:rw --network host --pid host --privileged -w /app vpn_telegram-bot:latest python -m bot.main")

time.sleep(10)

print("\n=== Final check ===")
run("docker ps")
run("docker logs vpn_telegram_bot --tail=20")

print("\n✅ DONE! Bot should work now!")
client.close()
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

print("=== Check containers ===")
run("docker ps -a | grep vpn")

print("\n=== Install aiosqlite (async) ===")
# Start installation without waiting
stdin, stdout, stderr = client.exec_command("docker exec vpn_fix_temp pip install aiosqlite")
print("Installation started...")

time.sleep(30)  # Wait for installation

print("\n=== Commit and start ===")
run("docker commit vpn_fix_temp vpn_telegram-bot:latest")
run("docker rm -f vpn_fix_temp")
run("docker run -d --name vpn_telegram_bot --restart unless-stopped --env-file /root/vpn_telegram/.env -v /root/vpn_telegram:/app -v /root/vpn_telegram/data:/app/data -v /etc/x-ui:/etc/x-ui:rw --network host --pid host --privileged -w /app vpn_telegram-bot:latest python -m bot.main")

time.sleep(10)

print("\n=== Check result ===")
run("docker ps")
run("docker logs vpn_telegram_bot --tail=20")

client.close()
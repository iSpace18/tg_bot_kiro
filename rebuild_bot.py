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

print("=== Step 1: Stop and remove current container ===")
run("cd ~/vpn_telegram && docker compose down")

print("\n=== Step 2: Remove old image ===")
run("docker rmi vpn_telegram-bot || true")

print("\n=== Step 3: Rebuild and start ===")
run("cd ~/vpn_telegram && docker compose up -d --build", timeout=300)
time.sleep(15)

print("\n=== Step 4: Check status ===")
run("docker ps")

print("\n=== Step 5: Check logs ===")
run("docker logs vpn_telegram_bot --tail=50")

print("\n✅ DONE! Bot should be working now.")
client.close()

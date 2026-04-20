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

print("=== Step 1: Install pydantic-settings in running container ===")
run("docker exec vpn_telegram_bot pip install pydantic-settings", timeout=60)

print("\n=== Step 2: Restart bot ===")
run("docker restart vpn_telegram_bot")
time.sleep(10)

print("\n=== Step 3: Check logs ===")
run("docker logs vpn_telegram_bot --tail=50")

print("\n=== Step 4: Commit updated image ===")
run("docker commit vpn_telegram_bot vpn_telegram-bot:latest")

print("\n✅ DONE! Bot should be fully working now.")
client.close()

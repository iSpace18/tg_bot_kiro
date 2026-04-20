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

print("=== Install aiosqlite in running container ===")
# Install aiosqlite directly
stdin, stdout, stderr = client.exec_command("docker exec vpn_telegram_bot pip install aiosqlite")
print("Installing aiosqlite...")

# Wait for installation
time.sleep(30)

print("\n=== Restart bot ===")
run("docker restart vpn_telegram_bot")
time.sleep(10)

print("\n=== Check logs ===")
run("docker logs vpn_telegram_bot --tail=30")

print("\n=== Check status ===")
run("docker ps | grep vpn")

print("\n=== Test if packages are installed ===")
run("docker exec vpn_telegram_bot pip list | grep -E 'aiogram|aiosqlite|sqlalchemy'")

print("\n✅ Final attempt - bot should be working now!")
client.close()
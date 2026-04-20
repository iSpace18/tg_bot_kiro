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

print("=== Install aiosqlite in running container ===")
# Install aiosqlite directly in the running container
stdin, stdout, stderr = client.exec_command("docker exec vpn_telegram_bot pip install aiosqlite", timeout=180)
print("Installing aiosqlite...")
time.sleep(45)  # Wait for installation

print("\n=== Restart bot ===")
run("docker restart vpn_telegram_bot")
time.sleep(15)

print("\n=== Check logs ===")
run("docker logs vpn_telegram_bot --tail=50")

print("\n=== If working, commit the image ===")
result = run("docker logs vpn_telegram_bot --tail=5")
if "Bot starting" in result:
    print("✅ Bot is working! Committing image...")
    run("docker commit vpn_telegram_bot vpn_telegram-bot:latest")
    print("✅ Image committed")
else:
    print("❌ Bot still not working")

print("\n=== Final status ===")
run("docker ps | grep vpn")

print("\n🎉 Test /start and buttons now!")
client.close()
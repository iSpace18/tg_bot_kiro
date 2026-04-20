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

print("\n=== Check available images ===")
run("docker images | grep vpn")

print("\n=== Use the working image with packages ===")
# Use the image that had packages installed (sha256:1138b31d7a3c717c73c7c8e8952246f7f95768dbafa82ec672d0fa019e853787)
run("docker tag 1138b31d7a3c717c73c7c8e8952246f7f95768dbafa82ec672d0fa019e853787 vpn_telegram-bot:working")

print("\n=== Create temp container to add aiosqlite ===")
run("docker run -d --name vpn_add_aiosqlite vpn_telegram-bot:working sleep 3600")

print("\n=== Install aiosqlite quickly ===")
# Try to install just aiosqlite
stdin, stdout, stderr = client.exec_command("docker exec vpn_add_aiosqlite pip install aiosqlite")
print("Installing aiosqlite...")
time.sleep(20)  # Wait for installation

print("\n=== Commit working image ===")
run("docker commit vpn_add_aiosqlite vpn_telegram-bot:latest")

print("\n=== Cleanup ===")
run("docker rm -f vpn_add_aiosqlite")

print("\n=== Start bot with working image ===")
run("docker run -d --name vpn_telegram_bot --restart unless-stopped --env-file /root/vpn_telegram/.env -v /root/vpn_telegram:/app -v /root/vpn_telegram/data:/app/data -v /etc/x-ui:/etc/x-ui:rw --network host --pid host --privileged -w /app vpn_telegram-bot:latest python -m bot.main")

time.sleep(15)

print("\n=== Final status ===")
run("docker ps")
run("docker logs vpn_telegram_bot --tail=20")

print("\n✅ Bot should be working now!")
client.close()
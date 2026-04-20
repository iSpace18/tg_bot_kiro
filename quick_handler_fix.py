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

print("=== Fix handler imports ===")
# Replace AsyncSession with Session in all handlers
run("find /root/vpn_telegram/bot/handlers -name '*.py' -exec sed -i 's/from sqlalchemy.ext.asyncio import AsyncSession/from sqlalchemy.orm import Session/g' {} \\;")
run("find /root/vpn_telegram/bot/handlers -name '*.py' -exec sed -i 's/session: AsyncSession/session: Session/g' {} \\;")
run("find /root/vpn_telegram/bot/handlers -name '*.py' -exec sed -i 's/await session.execute/session.execute/g' {} \\;")
run("find /root/vpn_telegram/bot/handlers -name '*.py' -exec sed -i 's/await session.commit/session.commit/g' {} \\;")
run("find /root/vpn_telegram/bot/handlers -name '*.py' -exec sed -i 's/await session.refresh/session.refresh/g' {} \\;")

print("\n=== Restart bot ===")
run("docker restart vpn_telegram_bot")
time.sleep(15)

print("\n=== Check logs ===")
run("docker logs vpn_telegram_bot --tail=50")

print("\n=== Check status ===")
run("docker ps | grep vpn")

print("\n✅ Handlers fixed for sync SQLite")
client.close()
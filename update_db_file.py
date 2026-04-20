import paramiko
import time

HOST = "89.44.76.190"
USER = "root"
PASS = "Mb69Bs5T18hNvrw5FC"

# New db.py content
db_content = '''import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from bot.models import Base
from bot.config import settings

os.makedirs("data", exist_ok=True)

# Use regular SQLite engine
engine = create_engine(settings.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    return SessionLocal()
'''

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

print("=== Update db.py on server ===")
stdin, stdout, stderr = client.exec_command("cat > /root/vpn_telegram/bot/utils/db.py")
stdin.write(db_content)
stdin.close()

print("✅ db.py updated")

print("\n=== Restart bot ===")
run("docker restart vpn_telegram_bot")
time.sleep(10)

print("\n=== Check logs ===")
run("docker logs vpn_telegram_bot --tail=30")

print("\n=== Check if bot is running properly ===")
run("docker ps | grep vpn")

print("\n🎉 Bot should be working now! Test buttons: 🎁 Пробный период and 💳 Купить VPN")
client.close()
import paramiko
import time

HOST, USER, PASS = "89.44.76.190", "root", "Mb69Bs5T18hNvrw5FC"

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username='root', password=PASS, timeout=30)

    def run(cmd, timeout=120):
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode()
        if out: print(out)
        return out.strip()

    print("=== Installing packages in temp container ===")
    result = run("docker exec vpn_telegram_bot_temp pip install aiogram==3.10.0 sqlalchemy==2.0.36 asyncpg yookassa 2>&1 | tail -30", timeout=180)
    
    if "Successfully installed" in result or "Requirement already satisfied" in result:
        print("\n✅ Packages installed!")
    else:
        print("\n⚠️ Package install may have failed, but continuing...")
    
    print("\n=== Committing container as image ===")
    run("docker commit vpn_telegram_bot_temp vpn_telegram-bot:latest")
    
    print("\n=== Cleaning up temp container ===")
    run("docker rm -f vpn_telegram_bot_temp")
    
    print("\n=== Starting bot ===")
    run("cd ~/vpn_telegram && docker compose up -d")
    time.sleep(10)
    
    print("\n=== Status ===")
    run("docker ps | grep vpn")
    
    print("\n=== Logs ===")
    run("docker logs vpn_telegram_bot --tail=30 2>&1")
    
    print("\n✅ DONE! Check if bot responds to buttons now.")
    
    client.close()
except Exception as e:
    print(f"Error: {e}")

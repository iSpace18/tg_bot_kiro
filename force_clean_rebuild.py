import paramiko
import time

HOST, USER, PASS = "89.44.76.190", "root", "Mb69Bs5T18hNvrw5FC"

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=30)

    def run(cmd, timeout=120):
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode()
        if out: print(out)
        return out.strip()

    print("=== Stopping containers ===")
    run("cd ~/vpn_telegram && docker compose down")
    
    print("\n=== Removing old images ===")
    run("docker rmi vpn_telegram-bot:latest 2>&1 || true")
    run("docker system prune -f")
    
    print("\n=== Uploading fresh code ===")
    sftp = client.open_sftp()
    
    with open('bot/handlers/payment.py', 'r', encoding='utf-8') as f:
        content = f.read()
    with sftp.open('/root/vpn_telegram/bot/handlers/payment.py', 'w') as f:
        f.write(content)
    print("✅ payment.py")
    
    sftp.close()
    
    print("\n=== Building from scratch (no cache) ===")
    run("cd ~/vpn_telegram && docker compose build --no-cache")
    
    print("\n=== Starting ===")
    run("cd ~/vpn_telegram && docker compose up -d")
    time.sleep(12)
    
    print("\n=== Bot Logs ===")
    run("docker logs vpn_telegram_bot --tail=20 2>&1")
    
    print("\n✅ Done! Try buttons now.")
    
    client.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

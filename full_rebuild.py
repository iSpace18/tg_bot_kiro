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

    print("=== Uploading all files ===")
    sftp = client.open_sftp()
    
    files = [
        'bot/handlers/payment.py',
        'bot/services/vpn_service.py',
        'bot/keyboards/main.py'
    ]
    
    for f in files:
        with open(f, 'r', encoding='utf-8') as fh:
            content = fh.read()
        with sftp.open(f'/root/vpn_telegram/{f}', 'w') as fh:
            fh.write(content)
        print(f"✅ {f}")
    
    sftp.close()

    print("\n=== Full rebuild ===")
    run("cd ~/vpn_telegram && docker compose down")
    time.sleep(3)
    run("cd ~/vpn_telegram && docker compose up -d --build --force-recreate")
    time.sleep(12)

    print("\n=== Bot Logs ===")
    logs = run("docker logs vpn_telegram_bot --tail=25 2>&1")
    
    if "Starting bot" in logs and "error" not in logs.lower():
        print("\n✅ Bot started successfully!")
    else:
        print("\n⚠️ Check logs above")

    # Commit
    run("cd ~/vpn_telegram && git add -A && git commit -m 'Fix: handlers with session' && git push origin main")

    client.close()
except Exception as e:
    print(f"Error: {e}")

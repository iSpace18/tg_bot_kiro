import paramiko
import time

HOST, USER, PASS = "89.44.76.190", "root", "Mb69Bs5T18hNvrw5FC"

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=30)

    def run(cmd, timeout=60):
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode()
        if out: print(out)
        return out.strip()

    sftp = client.open_sftp()
    for f in ['bot/keyboards/main.py', 'bot/services/vpn_service.py', 'bot/handlers/payment.py']:
        with open(f, 'r', encoding='utf-8') as fh:
            content = fh.read()
        with sftp.open(f'/root/vpn_telegram/{f}', 'w') as fh:
            fh.write(content)
        print(f"✅ Uploaded {f}")
    sftp.close()

    run("cd ~/vpn_telegram && docker compose down", timeout=60)
    time.sleep(2)
    run("cd ~/vpn_telegram && docker compose up -d --build", timeout=120)
    time.sleep(10)

    print("\n=== Bot Logs ===")
    logs = run("docker logs vpn_telegram_bot --tail=15 2>&1")

    if "error" in logs.lower() or "Error" in logs:
        print("\n❌ Still errors!")
    else:
        print("\n✅ Bot started successfully!")

    client.close()
except Exception as e:
    print(f"Error: {e}")

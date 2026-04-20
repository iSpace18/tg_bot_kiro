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
    for f in ['bot/services/vpn_service.py', 'bot/handlers/payment.py']:
        with open(f, 'r', encoding='utf-8') as fh:
            content = fh.read()
        with sftp.open(f'/root/vpn_telegram/{f}', 'w') as fh:
            fh.write(content)
        print(f"✅ Uploaded {f}")
    sftp.close()

    run("sqlite3 /root/vpn_telegram/data/bot.db \"UPDATE users SET trial_used = 0 WHERE telegram_id = 1658346274;\"")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"DELETE FROM vpn_keys;\"")

    run("cd ~/vpn_telegram && docker compose down", timeout=60)
    time.sleep(2)
    run("cd ~/vpn_telegram && docker compose up -d --build", timeout=120)
    time.sleep(10)

    print("\n=== Bot Logs ===")
    run("docker logs vpn_telegram_bot --tail=10 2>&1")

    # Commit to GitHub
    run("cd ~/vpn_telegram && git add -A && git commit -m 'Fix: beautiful name, connection instructions' && git push origin main")

    print("\n✅ Done! Get a trial key now.")
    client.close()
except Exception as e:
    print(f"Error: {e}")

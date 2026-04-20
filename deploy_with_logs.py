import paramiko
import time

HOST, USER, PASS = "89.44.76.190", "root", "Mb69Bs5T18hNvrw5FC"

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=30)

    def run(cmd, timeout=30):
        _, stdout, _ = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode()
        if out: print(out)

    sftp = client.open_sftp()
    with open('bot/services/vpn_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    with sftp.open('/root/vpn_telegram/bot/services/vpn_service.py', 'w') as f:
        f.write(content)
    sftp.close()
    print("✅ Uploaded with logs")

    run("sqlite3 /root/vpn_telegram/data/bot.db \"UPDATE users SET trial_used = 0 WHERE telegram_id = 1658346274;\"")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"DELETE FROM vpn_keys;\"")

    run("cd ~/vpn_telegram && docker compose restart")
    time.sleep(8)

    print("\n=== Bot logs ===")
    run("docker logs vpn_telegram_bot --tail=10 2>&1")

    print("\n✅ Try getting key now and check logs!")

    client.close()
except Exception as e:
    print(f"Error: {e}")

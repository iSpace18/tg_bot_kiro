import paramiko
import time

HOST, USER, PASS = "89.44.76.190", "root", "Mb69Bs5T18hNvrw5FC"

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=30)

    def run(cmd, timeout=30):
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode()
        err = stderr.read().decode()
        if out: print(out)
        if err: print(f"Error: {err}")
        return out

    # Upload updated code
    sftp = client.open_sftp()
    with open('bot/services/vpn_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    with sftp.open('/root/vpn_telegram/bot/services/vpn_service.py', 'w') as f:
        f.write(content)
    sftp.close()
    print("✅ Uploaded vpn_service.py")

    # Reset trial and delete keys
    print("\n=== Resetting Trial ===")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"UPDATE users SET trial_used = 0 WHERE telegram_id = 1658346274;\"")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"DELETE FROM vpn_keys;\"")
    print("✅ Trial reset")

    # Rebuild bot (no cache to ensure fresh code)
    print("\n=== Rebuilding Bot ===")
    run("cd ~/vpn_telegram && docker compose down", timeout=60)
    time.sleep(2)
    run("cd ~/vpn_telegram && docker compose up -d --build", timeout=120)
    time.sleep(10)

    print("\n=== Bot Logs (last 20 lines) ===")
    run("docker logs vpn_telegram_bot --tail=20 2>&1")

    print("\n✅ Deployment complete!")
    print("\n🔑 Now get a trial key from the bot and check:")
    print("1. The URL should have security=reality")
    print("2. It should have pbk= parameter with the public key")
    print("3. Test it in v2rayNG on mobile network")

    client.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

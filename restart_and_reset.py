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
        if out: print(out)
        return out

    print("=== Resetting Trial ===")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"UPDATE users SET trial_used = 0 WHERE telegram_id = 1658346274;\"")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"DELETE FROM vpn_keys;\"")
    print("✅ Trial reset")

    print("\n=== Restarting Bot ===")
    run("cd ~/vpn_telegram && docker compose restart")
    time.sleep(8)

    print("\n=== Bot Logs ===")
    run("docker logs vpn_telegram_bot --tail=15 2>&1")

    print("\n✅ Ready! Get a trial key now.")

    client.close()
except Exception as e:
    print(f"Error: {e}")

import paramiko

HOST, USER, PASS = "89.44.76.190", "root", "Mb69Bs5T18hNvrw5FC"

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=30)

    def run(cmd, timeout=30):
        print(f"$ {cmd}")
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode()
        err = stderr.read().decode()
        if out: print(out)
        if err and 'warning' not in err.lower(): print("ERR:", err)

    print("=== Check vpn_service.py on server ===")
    run("grep -A 5 'security == \"reality\"' /root/vpn_telegram/bot/services/vpn_service.py")

    print("\n=== Check Reality in DB ===")
    run("sqlite3 /etc/x-ui/x-ui.db \"SELECT json_extract(stream_settings, '$.security') FROM inbounds WHERE protocol='vless';\"")

    print("\n=== Bot logs ===")
    run("docker logs vpn_telegram_bot --tail=20 2>&1 | grep -E 'ERROR|Client|reality|security'")

    print("\n=== Rebuild bot (force reload code) ===")
    run("cd ~/vpn_telegram && docker compose down")
    run("cd ~/vpn_telegram && docker compose build --no-cache 2>&1 | tail -5", timeout=180)
    run("cd ~/vpn_telegram && docker compose up -d")

    import time
    time.sleep(8)

    print("\n=== Reset trial again ===")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"UPDATE users SET trial_used = 0 WHERE telegram_id = 1658346274;\"")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"DELETE FROM vpn_keys;\"")
    run("cd ~/vpn_telegram && docker compose restart")
    time.sleep(5)

    print("\n=== Check bot status ===")
    run("cd ~/vpn_telegram && docker compose ps")
    run("docker logs vpn_telegram_bot --tail=5 2>&1")

    print("\n✅ Bot rebuilt. Try getting new key now!")

    client.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

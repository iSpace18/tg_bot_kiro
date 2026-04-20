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
        return out.strip()

    print("=== Waiting for you to get trial key from bot ===")
    print("Please get a trial key now...")
    time.sleep(5)

    print("\n=== Checking Bot Logs ===")
    logs = run("docker logs vpn_telegram_bot --tail=30 2>&1")
    print(logs)

    print("\n=== Checking Generated VPN Key ===")
    key_data = run("sqlite3 /root/vpn_telegram/data/bot.db \"SELECT subscription_url FROM vpn_keys ORDER BY created_at DESC LIMIT 1;\"")
    
    if key_data:
        print(f"\n🔑 Generated URL:")
        print(key_data)
        
        # Parse URL to check parameters
        if "security=reality" in key_data:
            print("\n✅ Security: reality")
        else:
            print("\n❌ Security: NOT reality")
        
        if "pbk=" in key_data:
            pbk_start = key_data.find("pbk=") + 4
            pbk_end = key_data.find("&", pbk_start)
            if pbk_end == -1:
                pbk_end = key_data.find("#", pbk_start)
            pbk = key_data[pbk_start:pbk_end]
            print(f"✅ Public Key: {pbk[:30]}...")
        else:
            print("❌ No public key found")
        
        if "sni=" in key_data:
            print("✅ SNI present")
        
        if "sid=" in key_data:
            print("✅ Short ID present")
    else:
        print("\n⚠️ No VPN key found yet. Please get a trial key from the bot first.")

    client.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

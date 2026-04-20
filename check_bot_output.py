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
        return out.strip()

    print("=== Waiting for you to get trial key ===")
    print("Get a trial key now, then wait 5 seconds...")
    time.sleep(10)
    
    print("\n=== Bot Logs (last 30 lines) ===")
    run("docker logs vpn_telegram_bot --tail=30 2>&1")
    
    print("\n=== Checking Generated Key in Database ===")
    key = run("sqlite3 /root/vpn_telegram/data/bot.db \"SELECT subscription_url FROM vpn_keys ORDER BY created_at DESC LIMIT 1;\"")
    
    if key:
        print(f"\n🔑 Key from database:")
        print(key)
        
        # Count how many URLs
        url_count = key.count("vless://")
        print(f"\n📊 Number of URLs: {url_count}")
        
        if url_count == 1:
            print("❌ Only 1 URL found - bot is not generating both")
        elif url_count == 2:
            print("✅ 2 URLs found - correct!")
        
        # Check ports
        if ":443" in key:
            print("✅ Port 443 present")
        if ":80" in key:
            print("✅ Port 80 present")
    else:
        print("\n⚠️ No key found yet")

    client.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

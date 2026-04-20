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

    print("=== Current Configuration ===")
    
    # Check port in database
    port = run("sqlite3 /etc/x-ui/x-ui.db \"SELECT port FROM inbounds WHERE protocol='vless' LIMIT 1;\"")
    print(f"Database port: {port}")
    
    # Check what xray is listening on
    print("\n=== Xray Listening Ports ===")
    run("ss -tlnp | grep xray")
    
    # Check stream settings
    print("\n=== Stream Settings ===")
    stream = run("sqlite3 /etc/x-ui/x-ui.db \"SELECT json_extract(stream_settings, '$.network'), json_extract(stream_settings, '$.security') FROM inbounds WHERE protocol='vless' LIMIT 1;\"")
    print(f"Network|Security: {stream}")
    
    # Test port 443 from outside
    print("\n=== Testing Port 443 from Outside ===")
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((HOST, 443))
        sock.close()
        if result == 0:
            print("✅ Port 443 is accessible")
        else:
            print("❌ Port 443 is NOT accessible")
    except Exception as e:
        print(f"Test error: {e}")
    
    print("\n=== Waiting for you to get a trial key ===")
    print("Please get a trial key from the bot now...")
    time.sleep(10)
    
    print("\n=== Checking Generated Key ===")
    key = run("sqlite3 /root/vpn_telegram/data/bot.db \"SELECT subscription_url FROM vpn_keys ORDER BY created_at DESC LIMIT 1;\"")
    
    if key:
        print(f"\n🔑 Generated URL:")
        print(key)
        
        # Parse URL
        if ":443" in key:
            print("\n✅ Port: 443")
        elif ":2053" in key:
            print("\n⚠️ Port: 2053 (not 443)")
        elif ":8443" in key:
            print("\n⚠️ Port: 8443 (not 443)")
        
        if "security=reality" in key:
            print("✅ Security: reality")
        else:
            print("❌ Security: NOT reality")
        
        if "type=tcp" in key:
            print("✅ Type: tcp")
        elif "type=grpc" in key:
            print("⚠️ Type: grpc (should be tcp)")
        
        if "pbk=" in key:
            print("✅ Public key present")
        
        if "sni=www.microsoft.com" in key:
            print("✅ SNI: www.microsoft.com")
        elif "sni=www.amd.com" in key:
            print("⚠️ SNI: www.amd.com (old)")
    else:
        print("\n⚠️ No key found. Get a trial key first!")
    
    print("\n=== Bot Logs (last 15 lines) ===")
    run("docker logs vpn_telegram_bot --tail=15 2>&1")

    client.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

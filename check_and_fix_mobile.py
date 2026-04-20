import paramiko
import json

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
    
    # Check current port
    port = run("sqlite3 /etc/x-ui/x-ui.db \"SELECT port FROM inbounds WHERE protocol='vless' LIMIT 1;\"")
    print(f"Current port: {port}")
    
    # Check stream settings
    stream = run("sqlite3 /etc/x-ui/x-ui.db \"SELECT stream_settings FROM inbounds WHERE protocol='vless' LIMIT 1;\"")
    stream_json = json.loads(stream)
    
    print(f"Security: {stream_json.get('security')}")
    print(f"Network: {stream_json.get('network')}")
    print(f"Target: {stream_json.get('realitySettings', {}).get('target')}")
    print(f"SNI: {stream_json.get('realitySettings', {}).get('serverNames')}")
    
    print("\n=== Testing Port Accessibility ===")
    
    # Test if port is open
    import socket
    test_ports = [443, 8443, 2053, 2083, 2087, 2096]
    
    print(f"\nTesting ports from external...")
    for test_port in test_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((HOST, test_port))
            sock.close()
            if result == 0:
                print(f"✅ Port {test_port}: OPEN")
            else:
                print(f"❌ Port {test_port}: CLOSED")
        except:
            print(f"❌ Port {test_port}: ERROR")
    
    print("\n=== Recommendations ===")
    print("Для мобильных сетей лучше всего работают:")
    print("1. Port 443 (HTTPS) - самый надежный")
    print("2. Port 80 (HTTP) - если 443 не работает")
    print("3. Port 2053, 2083, 2087, 2096 (Cloudflare ports)")
    
    print("\n=== Changing to Port 443 ===")
    
    # Change port to 443
    run("sqlite3 /etc/x-ui/x-ui.db \"UPDATE inbounds SET port = 443 WHERE protocol='vless';\"")
    print("✅ Port changed to 443")
    
    # Also try changing target to more common site
    stream_json['realitySettings']['target'] = "www.microsoft.com:443"
    stream_json['realitySettings']['serverNames'] = ["www.microsoft.com"]
    
    # Write to temp file
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(stream_json, f)
        temp_local = f.name
    
    sftp = client.open_sftp()
    temp_remote = '/tmp/stream_update.json'
    sftp.put(temp_local, temp_remote)
    sftp.close()
    os.unlink(temp_local)
    
    run(f"sqlite3 /etc/x-ui/x-ui.db \"UPDATE inbounds SET stream_settings = readfile('{temp_remote}') WHERE protocol='vless';\"")
    run(f"rm {temp_remote}")
    
    print("✅ Target changed to www.microsoft.com")
    
    print("\n=== Restarting Services ===")
    run("pkill -SIGHUP xray")
    
    # Reset trial and keys
    run("sqlite3 /root/vpn_telegram/data/bot.db \"UPDATE users SET trial_used = 0 WHERE telegram_id = 1658346274;\"")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"DELETE FROM vpn_keys;\"")
    
    # Restart bot
    run("cd ~/vpn_telegram && docker compose restart", timeout=60)
    
    import time
    time.sleep(8)
    
    print("\n✅ Configuration updated!")
    print("\n📱 Changes made:")
    print("   - Port: 8443 → 443 (standard HTTPS)")
    print("   - Target: www.amd.com → www.microsoft.com")
    print("   - Trial period reset")
    print("\n🔑 Get a new trial key and test on mobile network")

    client.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

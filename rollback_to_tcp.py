import paramiko
import json
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

    print("=== Rolling back to TCP + Reality (working config) ===")
    
    # Create clean working config
    clean_config = {
        "network": "tcp",
        "security": "reality",
        "externalProxy": [],
        "realitySettings": {
            "show": False,
            "xver": 0,
            "target": "www.microsoft.com:443",
            "serverNames": ["www.microsoft.com"],
            "privateKey": "8MmHQot3UM5xzcPsXP43hJPPBr-d6Z-7f16Ei8qFsWg",
            "minClientVer": "",
            "maxClientVer": "",
            "maxTimediff": 0,
            "shortIds": ["2587", "4289105666", "575ea79757e6", "4b", "98145b", "3343be4e90984128", "ad06a3d4", "ebad52624a9c31"],
            "mldsa65Seed": "",
            "settings": {
                "publicKey": "nV51ajbOIubsVbDtRNfgaNYF0_Giy8pm819uBi6D2xo",
                "fingerprint": "chrome",
                "serverName": "",
                "spiderX": "/",
                "mldsa65Verify": ""
            }
        },
        "tcpSettings": {
            "acceptProxyProtocol": False,
            "header": {"type": "none"}
        }
    }
    
    # Write to temp file
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(clean_config, f)
        temp_local = f.name
    
    sftp = client.open_sftp()
    temp_remote = '/tmp/stream_tcp_clean.json'
    sftp.put(temp_local, temp_remote)
    sftp.close()
    os.unlink(temp_local)
    
    # Update database
    run(f"sqlite3 /etc/x-ui/x-ui.db \"UPDATE inbounds SET stream_settings = readfile('{temp_remote}') WHERE protocol='vless';\"")
    run(f"rm {temp_remote}")
    
    print("✅ Restored TCP + Reality config")
    
    # Check which ports are actually open and working
    print("\n=== Checking Open Ports ===")
    ports_check = run("ss -tlnp | grep xray || ss -tlnp | grep x-ui")
    
    # Try port 443 first (most reliable for mobile)
    print("\n=== Setting Port to 443 ===")
    run("sqlite3 /etc/x-ui/x-ui.db \"UPDATE inbounds SET port = 443 WHERE protocol='vless';\"")
    
    print("\n=== Restarting Xray ===")
    run("pkill -SIGHUP xray")
    time.sleep(3)
    
    # Verify xray is running
    print("\n=== Verifying Xray ===")
    xray_status = run("ps aux | grep xray | grep -v grep")
    if "xray" in xray_status:
        print("✅ Xray is running")
    else:
        print("❌ Xray is NOT running - restarting x-ui service")
        run("systemctl restart x-ui")
        time.sleep(5)
    
    # Check listening ports
    print("\n=== Checking Listening Ports ===")
    run("ss -tlnp | grep ':443\\|:2053\\|:8443' || echo 'No ports listening'")
    
    # Reset trial
    print("\n=== Resetting Trial ===")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"UPDATE users SET trial_used = 0 WHERE telegram_id = 1658346274;\"")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"DELETE FROM vpn_keys;\"")
    
    # Restart bot
    print("\n=== Restarting Bot ===")
    run("cd ~/vpn_telegram && docker compose restart", timeout=60)
    time.sleep(8)
    
    print("\n=== Bot Logs ===")
    run("docker logs vpn_telegram_bot --tail=20 2>&1")
    
    print("\n✅ Rollback complete!")
    print("\n📱 Configuration:")
    print("   - Port: 443 (standard HTTPS)")
    print("   - Security: Reality")
    print("   - Network: TCP")
    print("   - Target: www.microsoft.com")
    print("\n🔑 Get a new trial key and test")

    client.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

import paramiko
import json
import uuid
import time

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
        return out

    print("=== Generating Reality keys ===")
    keys_output = run("/usr/local/x-ui/bin/xray-linux-amd64 x25519")
    
    # Parse keys
    private_key = ""
    public_key = ""
    for line in keys_output.split('\n'):
        if 'Private key:' in line:
            private_key = line.split(':')[1].strip()
        if 'Public key:' in line:
            public_key = line.split(':')[1].strip()
    
    print(f"Private: {private_key}")
    print(f"Public: {public_key}")

    # Generate short IDs
    short_id = uuid.uuid4().hex[:8]
    print(f"Short ID: {short_id}")

    print("\n=== Backing up current inbound ===")
    run("sqlite3 /etc/x-ui/x-ui.db \"SELECT settings, stream_settings FROM inbounds WHERE protocol='vless';\" > /tmp/backup_inbound.txt")

    print("\n=== Creating Reality inbound ===")
    
    # Reality stream settings
    stream_settings = {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
            "show": False,
            "dest": "www.microsoft.com:443",  # Destination to mimic
            "xver": 0,
            "serverNames": ["www.microsoft.com", "microsoft.com"],
            "privateKey": private_key,
            "shortIds": [short_id, ""]
        },
        "tcpSettings": {
            "acceptProxyProtocol": False,
            "header": {
                "type": "none"
            }
        }
    }

    # Update inbound with Reality
    run(f"""python3 << 'PYEOF'
import sqlite3, json
conn = sqlite3.connect('/etc/x-ui/x-ui.db', timeout=30)
cursor = conn.cursor()

# Get current inbound
cursor.execute("SELECT id, settings FROM inbounds WHERE protocol='vless'")
row = cursor.fetchone()
if row:
    inbound_id, settings_str = row
    settings = json.loads(settings_str)
    
    # Keep only first client or create new
    if settings.get('clients'):
        settings['clients'] = [settings['clients'][0]]
    else:
        settings['clients'] = []
    
    # Update port and stream settings
    cursor.execute("UPDATE inbounds SET port = 443 WHERE id = ?", (inbound_id,))
    cursor.execute("UPDATE inbounds SET stream_settings = ? WHERE id = ?", 
                   (json.dumps({json.dumps(stream_settings)}), inbound_id))
    
    conn.commit()
    print(f"Updated inbound {{inbound_id}} with Reality")
conn.close()
PYEOF""")

    print("\n=== Restarting x-ui ===")
    run("systemctl restart x-ui")
    time.sleep(8)

    print("\n=== Verify Reality config ===")
    run("cat /usr/local/x-ui/bin/config.json | python3 -c \"import json,sys; d=json.load(sys.stdin); inb=[i for i in d.get('inbounds',[]) if i.get('protocol')=='vless']; print('Security:', inb[0].get('streamSettings',{}).get('security') if inb else 'NOT FOUND')\"")

    print("\n=== Reset trial for testing ===")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"UPDATE users SET trial_used = 0 WHERE telegram_id = 1658346274;\"")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"DELETE FROM vpn_keys WHERE user_id = (SELECT id FROM users WHERE telegram_id = 1658346274);\"")

    print("\n=== Restarting bot ===")
    run("cd ~/vpn_telegram && docker compose restart")
    time.sleep(5)

    print(f"\n✅ Reality configured!")
    print(f"Public Key: {public_key}")
    print(f"Short ID: {short_id}")
    print(f"Server Name: www.microsoft.com")
    print(f"\nGet new key from bot - it will have Reality encryption!")

    client.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

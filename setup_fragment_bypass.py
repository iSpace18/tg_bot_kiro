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

    print("=== Setting up Fragment for DPI Bypass ===")
    print("Fragment разбивает пакеты, обходя DPI мобильных операторов")
    
    # Add more inbounds with different configurations
    # Port 2053 - Cloudflare port, often not blocked
    # Port 8443 - Alternative HTTPS
    
    settings = run("sqlite3 /etc/x-ui/x-ui.db \"SELECT settings FROM inbounds WHERE id=1;\"")
    
    # Create inbound on port 2053 with WebSocket
    ws_2053 = {
        "network": "ws",
        "security": "none",
        "externalProxy": [],
        "wsSettings": {
            "acceptProxyProtocol": False,
            "path": "/",
            "headers": {
                "Host": "www.speedtest.net"
            }
        },
        "sockopt": {
            "tcpFastOpen": True,
            "tcpNoDelay": True
        }
    }
    
    # Create inbound on port 8443 with WebSocket
    ws_8443 = {
        "network": "ws",
        "security": "none",
        "externalProxy": [],
        "wsSettings": {
            "acceptProxyProtocol": False,
            "path": "/api",
            "headers": {
                "Host": "www.google.com"
            }
        },
        "sockopt": {
            "tcpFastOpen": True,
            "tcpNoDelay": True
        }
    }
    
    import tempfile
    import os
    
    # Upload configs
    sftp = client.open_sftp()
    
    for port, config, host in [(2053, ws_2053, "speedtest.net"), (8443, ws_8443, "google.com")]:
        # Check if inbound exists
        check = run(f"sqlite3 /etc/x-ui/x-ui.db \"SELECT id FROM inbounds WHERE port={port};\"")
        
        if check:
            print(f"Port {port} already exists, updating...")
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                json.dump(config, f)
                temp_local = f.name
            
            sftp.put(temp_local, f'/tmp/stream_{port}.json')
            os.unlink(temp_local)
            
            run(f"sqlite3 /etc/x-ui/x-ui.db \"UPDATE inbounds SET stream_settings = readfile('/tmp/stream_{port}.json') WHERE port={port};\"")
            run(f"rm /tmp/stream_{port}.json")
        else:
            print(f"Creating inbound on port {port}...")
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                json.dump(config, f)
                temp_stream = f.name
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                f.write(settings)
                temp_settings = f.name
            
            sftp.put(temp_stream, f'/tmp/stream_{port}.json')
            sftp.put(temp_settings, f'/tmp/settings_{port}.json')
            
            os.unlink(temp_stream)
            os.unlink(temp_settings)
            
            sniffing = '{\\"enabled\\":true,\\"destOverride\\":[\\"http\\",\\"tls\\"]}'
            insert = f"sqlite3 /etc/x-ui/x-ui.db \"INSERT INTO inbounds (user_id, up, down, total, remark, enable, expiry_time, listen, port, protocol, settings, stream_settings, tag, sniffing) VALUES (1, 0, 0, 0, 'WS-{port}-{host}', 1, 0, '', {port}, 'vless', readfile('/tmp/settings_{port}.json'), readfile('/tmp/stream_{port}.json'), 'inbound-{port}', '{sniffing}');\""
            run(insert)
            run(f"rm /tmp/stream_{port}.json /tmp/settings_{port}.json")
    
    sftp.close()
    
    print("\n✅ Added bypass inbounds")
    
    # Restart xray
    print("\n=== Restarting X-UI ===")
    run("systemctl restart x-ui")
    time.sleep(5)
    
    # Verify
    print("\n=== Verifying Inbounds ===")
    run("sqlite3 /etc/x-ui/x-ui.db \"SELECT id, port, remark FROM inbounds;\"")
    
    print("\n=== Listening Ports ===")
    run("ss -tlnp | grep xray | grep -E ':(80|443|2053|8443)'")
    
    # Reset and rebuild bot
    print("\n=== Resetting Trial ===")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"UPDATE users SET trial_used = 0 WHERE telegram_id = 1658346274;\"")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"DELETE FROM vpn_keys;\"")
    
    print("\n=== Restarting Bot ===")
    run("cd ~/vpn_telegram && docker compose restart", timeout=60)
    time.sleep(8)
    
    print("\n✅ Setup complete!")
    print("\n📱 Теперь у вас 4 конфигурации для обхода блокировок:")
    print("   1. Port 443 (Reality) - WiFi")
    print("   2. Port 80 (WebSocket) - базовый обход")
    print("   3. Port 2053 (WebSocket + speedtest.net host) - Cloudflare port")
    print("   4. Port 8443 (WebSocket + google.com host) - альтернативный HTTPS")
    print("\n🔑 Получите новый ключ - бот выдаст все 4 конфигурации")
    print("\n💡 Добавьте все в v2rayNG, клиент выберет рабочую")
    print("\n⚠️ Если не помогло - нужен домен + Cloudflare CDN")

    client.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

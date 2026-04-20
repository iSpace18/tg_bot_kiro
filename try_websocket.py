import paramiko
import json
import time

HOST, USER, PASS = "89.44.76.190", "root", "Mb69Bs5T18hNvrw5FC"

print("⚠️ Run this ONLY if gRPC doesn't work on mobile!")
print("Press Ctrl+C to cancel, or wait 5 seconds to continue...")
time.sleep(5)

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=30)

    def run(cmd, timeout=30):
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode()
        if out: print(out)
        return out.strip()

    print("\n=== Trying WebSocket Transport (best for mobile) ===")
    
    # Get current settings
    stream = run("sqlite3 /etc/x-ui/x-ui.db \"SELECT stream_settings FROM inbounds WHERE protocol='vless' LIMIT 1;\"")
    stream_json = json.loads(stream)
    
    # Change to WebSocket
    stream_json['network'] = 'ws'
    stream_json['wsSettings'] = {
        'path': '/ws',
        'headers': {
            'Host': 'www.microsoft.com'
        }
    }
    
    # Remove gRPC settings if present
    if 'grpcSettings' in stream_json:
        del stream_json['grpcSettings']
    
    print(f"Network: {stream_json.get('network')} → ws")
    
    # Write to temp file
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(stream_json, f)
        temp_local = f.name
    
    sftp = client.open_sftp()
    temp_remote = '/tmp/stream_ws.json'
    sftp.put(temp_local, temp_remote)
    sftp.close()
    os.unlink(temp_local)
    
    run(f"sqlite3 /etc/x-ui/x-ui.db \"UPDATE inbounds SET stream_settings = readfile('{temp_remote}') WHERE protocol='vless';\"")
    run(f"rm {temp_remote}")
    
    print("✅ Changed to WebSocket transport")
    
    print("\n=== Restarting Xray ===")
    run("pkill -SIGHUP xray")
    time.sleep(3)
    
    # Update bot code for WebSocket
    print("\n=== Updating Bot Code for WebSocket ===")
    
    # Read current code and update
    sftp = client.open_sftp()
    with sftp.open('/root/vpn_telegram/bot/services/vpn_service.py', 'r') as f:
        bot_code = f.read()
    sftp.close()
    
    # Add WebSocket support to URL generation
    ws_url_part = '''            # Build URL based on network type
            if network == "grpc":
                grpc_settings = stream_settings.get("grpcSettings", {})
                service_name = grpc_settings.get("serviceName", "grpc")
                
                sub_url = (
                    f"vless://{client_uuid}@{server_ip}:{port}"
                    f"?type=grpc&serviceName={service_name}&security=reality"
                    f"&pbk={public_key}&fp={fingerprint}&sni={sni}&sid={sid}&spx={spider_x_encoded}#{quote(display_name)}"
                )
            elif network == "ws":
                ws_settings = stream_settings.get("wsSettings", {})
                ws_path = ws_settings.get("path", "/")
                ws_host = ws_settings.get("headers", {}).get("Host", sni)
                
                sub_url = (
                    f"vless://{client_uuid}@{server_ip}:{port}"
                    f"?type=ws&path={quote(ws_path)}&host={ws_host}&security=reality"
                    f"&pbk={public_key}&fp={fingerprint}&sni={sni}&sid={sid}&spx={spider_x_encoded}#{quote(display_name)}"
                )
            else:
                # TCP
                sub_url = (
                    f"vless://{client_uuid}@{server_ip}:{port}"
                    f"?type=tcp&security=reality&pbk={public_key}&fp={fingerprint}"
                    f"&sni={sni}&sid={sid}&spx={spider_x_encoded}#{quote(display_name)}"
                )'''
    
    # Replace the URL generation part
    if 'elif network == "ws":' not in bot_code:
        bot_code = bot_code.replace(
            '            else:\n                # TCP',
            '            elif network == "ws":\n                ws_settings = stream_settings.get("wsSettings", {})\n                ws_path = ws_settings.get("path", "/")\n                ws_host = ws_settings.get("headers", {}).get("Host", sni)\n                \n                sub_url = (\n                    f"vless://{client_uuid}@{server_ip}:{port}"\n                    f"?type=ws&path={quote(ws_path)}&host={ws_host}&security=reality"\n                    f"&pbk={public_key}&fp={fingerprint}&sni={sni}&sid={sid}&spx={spider_x_encoded}#{quote(display_name)}"\n                )\n            else:\n                # TCP'
        )
    
    # Upload updated code
    sftp = client.open_sftp()
    with sftp.open('/root/vpn_telegram/bot/services/vpn_service.py', 'w') as f:
        f.write(bot_code)
    sftp.close()
    
    print("✅ Bot code updated for WebSocket")
    
    # Reset and restart
    print("\n=== Resetting Trial ===")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"UPDATE users SET trial_used = 0 WHERE telegram_id = 1658346274;\"")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"DELETE FROM vpn_keys;\"")
    
    print("\n=== Restarting Bot ===")
    run("cd ~/vpn_telegram && docker compose restart", timeout=60)
    time.sleep(8)
    
    print("\n✅ WebSocket configuration complete!")
    print("\n📱 Final settings:")
    print("   - Port: 2053")
    print("   - Security: Reality")
    print("   - Network: WebSocket (best for mobile)")
    print("   - Path: /ws")
    print("   - Target: www.microsoft.com")
    print("\n🔑 Get a new trial key and test on mobile network")
    print("\nℹ️ WebSocket - самый надежный вариант для мобильных сетей")

    client.close()
except KeyboardInterrupt:
    print("\n\nCancelled. Test gRPC first!")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

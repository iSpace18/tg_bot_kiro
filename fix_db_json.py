import paramiko
import json

HOST, USER, PASS = "89.44.76.190", "root", "Mb69Bs5T18hNvrw5FC"

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=30)

    print("=== Checking Current stream_settings ===")
    
    # Get current stream_settings
    cmd = """sqlite3 /etc/x-ui/x-ui.db "SELECT stream_settings FROM inbounds WHERE protocol='vless' LIMIT 1;" """
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    stream_raw = stdout.read().decode().strip()
    
    print("Raw stream_settings:")
    print(stream_raw[:200])
    
    try:
        # Try to parse it
        stream_json = json.loads(stream_raw)
        print("\n✅ JSON is valid")
        
        # Check if keys are present
        pbk = stream_json.get('realitySettings', {}).get('settings', {}).get('publicKey', '')
        pvk = stream_json.get('realitySettings', {}).get('privateKey', '')
        
        print(f"Public Key: {pbk[:30] if pbk else 'EMPTY'}...")
        print(f"Private Key: {pvk[:30] if pvk else 'EMPTY'}...")
        
        if not pbk or not pvk:
            print("\n⚠️ Keys are empty, regenerating...")
            
            # Generate new keys
            cmd = "/usr/local/x-ui/bin/xray-linux-amd64 x25519"
            stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
            output = stdout.read().decode()
            
            private_key = ""
            public_key = ""
            for line in output.split('\n'):
                if 'PrivateKey:' in line:
                    private_key = line.split('PrivateKey:')[1].strip()
                elif 'Password:' in line:
                    public_key = line.split('Password:')[1].strip()
            
            if private_key and public_key:
                print(f"\nNew Private: {private_key}")
                print(f"New Public: {public_key}")
                
                # Update JSON
                stream_json['realitySettings']['privateKey'] = private_key
                stream_json['realitySettings']['settings']['publicKey'] = public_key
                
                # Write to temp file and use sqlite3 to import
                import tempfile
                import os
                
                # Create temp file locally
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                    json.dump(stream_json, f)
                    temp_local = f.name
                
                # Upload to server
                sftp = client.open_sftp()
                temp_remote = '/tmp/stream_settings.json'
                sftp.put(temp_local, temp_remote)
                sftp.close()
                os.unlink(temp_local)
                
                # Update database using file
                cmd = f"""sqlite3 /etc/x-ui/x-ui.db "UPDATE inbounds SET stream_settings = readfile('{temp_remote}') WHERE protocol='vless';" """
                stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
                error = stderr.read().decode()
                
                if error:
                    print(f"\n❌ DB Error: {error}")
                else:
                    print("\n✅ Database updated successfully")
                    
                    # Verify
                    cmd = """sqlite3 /etc/x-ui/x-ui.db "SELECT stream_settings FROM inbounds WHERE protocol='vless' LIMIT 1;" """
                    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
                    verify = stdout.read().decode().strip()
                    verify_json = json.loads(verify)
                    
                    if verify_json['realitySettings']['settings']['publicKey'] == public_key:
                        print("✅ Verification passed")
                    else:
                        print("❌ Verification failed")
                
                # Cleanup
                cmd = f"rm {temp_remote}"
                client.exec_command(cmd)
                
                # Restart xray
                print("\n=== Restarting Xray ===")
                cmd = "pkill -SIGHUP xray"
                client.exec_command(cmd, timeout=10)
                print("✅ Xray restarted")
        
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON Parse Error: {e}")
        print("\nThis means the database has corrupted JSON. Let me fix it...")
        
        # Get the original working config
        cmd = """sqlite3 /etc/x-ui/x-ui.db "SELECT id, port FROM inbounds WHERE protocol='vless' LIMIT 1;" """
        stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
        info = stdout.read().decode().strip().split('|')
        inbound_id = info[0]
        port = info[1]
        
        # Generate keys
        cmd = "/usr/local/x-ui/bin/xray-linux-amd64 x25519"
        stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
        output = stdout.read().decode()
        
        private_key = ""
        public_key = ""
        for line in output.split('\n'):
            if 'PrivateKey:' in line:
                private_key = line.split('PrivateKey:')[1].strip()
            elif 'Password:' in line:
                public_key = line.split('Password:')[1].strip()
        
        # Create clean stream_settings
        clean_stream = {
            "network": "tcp",
            "security": "reality",
            "externalProxy": [],
            "realitySettings": {
                "show": False,
                "xver": 0,
                "target": "www.amd.com:443",
                "serverNames": ["www.amd.com"],
                "privateKey": private_key,
                "minClientVer": "",
                "maxClientVer": "",
                "maxTimediff": 0,
                "shortIds": ["2587", "4289105666", "575ea79757e6", "4b", "98145b", "3343be4e90984128", "ad06a3d4", "ebad52624a9c31"],
                "mldsa65Seed": "",
                "settings": {
                    "publicKey": public_key,
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
        
        print(f"\nNew Private: {private_key}")
        print(f"New Public: {public_key}")
        
        # Write to temp file
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(clean_stream, f)
            temp_local = f.name
        
        sftp = client.open_sftp()
        temp_remote = '/tmp/stream_settings_clean.json'
        sftp.put(temp_local, temp_remote)
        sftp.close()
        os.unlink(temp_local)
        
        # Update database
        cmd = f"""sqlite3 /etc/x-ui/x-ui.db "UPDATE inbounds SET stream_settings = readfile('{temp_remote}') WHERE protocol='vless';" """
        stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
        error = stderr.read().decode()
        
        if error:
            print(f"\n❌ DB Error: {error}")
        else:
            print("\n✅ Database fixed with clean JSON")
        
        # Cleanup
        cmd = f"rm {temp_remote}"
        client.exec_command(cmd)
        
        # Restart xray
        print("\n=== Restarting Xray ===")
        cmd = "pkill -SIGHUP xray"
        client.exec_command(cmd, timeout=10)
        print("✅ Xray restarted")

    client.close()
    
    print("\n✅ Done! Try getting a trial key now.")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

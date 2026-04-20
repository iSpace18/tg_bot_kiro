import paramiko
import json

HOST, USER, PASS = "89.44.76.190", "root", "Mb69Bs5T18hNvrw5FC"

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=30)

    print("=== Finding Xray Binary ===")
    
    # Find xray binary
    cmd = "find /usr -name 'xray*' -type f 2>/dev/null | head -5"
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    xray_paths = stdout.read().decode().strip().split('\n')
    print(f"Found: {xray_paths}")
    
    # Try common paths
    xray_binary = None
    for path in ['/usr/local/x-ui/bin/xray-linux-amd64', '/usr/bin/xray', '/usr/local/bin/xray'] + xray_paths:
        if path and path.strip():
            cmd = f"{path.strip()} version 2>&1 | head -1"
            stdin, stdout, stderr = client.exec_command(cmd, timeout=10)
            output = stdout.read().decode()
            if 'Xray' in output or 'xray' in output.lower():
                xray_binary = path.strip()
                print(f"✅ Using: {xray_binary}")
                break
    
    if not xray_binary:
        print("❌ Xray binary not found")
        client.close()
        exit(1)

    print("\n=== Generating Reality Keys ===")
    cmd = f"{xray_binary} x25519"
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    output = stdout.read().decode()
    error = stderr.read().decode()
    
    print(output)
    if error:
        print(f"Stderr: {error}")
    
    # Parse keys from output (format: PrivateKey: xxx, Password: xxx)
    private_key = ""
    public_key = ""
    for line in output.split('\n'):
        if 'PrivateKey:' in line:
            private_key = line.split('PrivateKey:')[1].strip()
        elif 'Password:' in line:
            public_key = line.split('Password:')[1].strip()
    
    if private_key and public_key:
        print(f"\n✅ Generated Keys:")
        print(f"Private: {private_key}")
        print(f"Public: {public_key}")
        
        # Update database with new keys
        print("\n=== Updating Database ===")
        
        # First, get current stream_settings
        cmd = """sqlite3 /etc/x-ui/x-ui.db "SELECT stream_settings FROM inbounds WHERE protocol='vless' LIMIT 1;" """
        stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
        stream_settings_raw = stdout.read().decode().strip()
        
        stream_json = json.loads(stream_settings_raw)
        stream_json['realitySettings']['privateKey'] = private_key
        stream_json['realitySettings']['settings']['publicKey'] = public_key
        
        # Update database - escape single quotes properly
        updated_json = json.dumps(stream_json).replace("'", "''")
        cmd = f"""sqlite3 /etc/x-ui/x-ui.db "UPDATE inbounds SET stream_settings = '{updated_json}' WHERE protocol='vless';" """
        stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
        error = stderr.read().decode()
        if error:
            print(f"DB Error: {error}")
        else:
            print("✅ Database updated with Reality keys")
        
        # Restart xray by sending SIGHUP
        print("\n=== Restarting Xray ===")
        cmd = "pkill -SIGHUP xray"
        stdin, stdout, stderr = client.exec_command(cmd, timeout=10)
        
        print("\n✅ Reality configured successfully!")
        print(f"\nPublic Key: {public_key}")
    else:
        print("❌ Failed to parse keys from output")

    client.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

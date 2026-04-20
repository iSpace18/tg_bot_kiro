import paramiko
import json

HOST, USER, PASS = "89.44.76.190", "root", "Mb69Bs5T18hNvrw5FC"

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=30)

    # Check stream_settings structure
    cmd = """sqlite3 /etc/x-ui/x-ui.db "SELECT id, port, stream_settings FROM inbounds WHERE protocol='vless' LIMIT 1;" """
    
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    output = stdout.read().decode()
    error = stderr.read().decode()
    
    if output:
        print("=== Raw DB Output ===")
        print(output)
        
        # Try to parse the stream_settings JSON
        parts = output.strip().split('|')
        if len(parts) >= 3:
            stream_settings_raw = parts[2]
            print("\n=== Stream Settings JSON ===")
            try:
                stream_json = json.loads(stream_settings_raw)
                print(json.dumps(stream_json, indent=2))
            except:
                print(f"Raw: {stream_settings_raw}")
    
    if error:
        print(f"Error: {error}")

    client.close()
except Exception as e:
    print(f"Error: {e}")

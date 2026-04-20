import paramiko
import time

HOST, USER, PASS = "89.44.76.190", "root", "Mb69Bs5T18hNvrw5FC"

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=30)

    def run(cmd, timeout=60):
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode()
        if out: print(out)
        return out.strip()

    print("=== Fixing Docker network ===")
    run("systemctl restart docker")
    time.sleep(5)
    
    print("\n=== Test network ===")
    run("docker run --rm python:3.11-slim ping -c 2 8.8.8.8 2>&1 || echo 'Network issue'")
    
    print("\n=== Build with network=host ===")
    run("cd ~/vpn_telegram && docker compose build --network=host", timeout=120)
    
    print("\n=== Start ===")
    run("cd ~/vpn_telegram && docker compose up -d")
    time.sleep(10)
    
    print("\n=== Logs ===")
    run("docker logs vpn_telegram_bot --tail=20 2>&1")
    
    client.close()
except Exception as e:
    print(f"Error: {e}")

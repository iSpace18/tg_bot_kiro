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

    print("=== Available images ===")
    run("docker images | grep vpn")
    
    print("\n=== Restoring from backup or using cached ===")
    # Try to pull from a working state
    run("cd ~/vpn_telegram && git stash")
    run("cd ~/vpn_telegram && git pull origin main")
    
    print("\n=== Starting with existing image ===")
    run("cd ~/vpn_telegram && docker compose up -d --no-build", timeout=30)
    time.sleep(10)
    
    print("\n=== Logs ===")
    run("docker logs vpn_telegram_bot --tail=25 2>&1")
    
    client.close()
except Exception as e:
    print(f"Error: {e}")

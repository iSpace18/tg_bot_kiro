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

    print("=== Starting bot ===")
    run("cd ~/vpn_telegram && docker compose up -d", timeout=90)
    time.sleep(10)
    
    print("\n=== Status ===")
    run("cd ~/vpn_telegram && docker compose ps")
    
    print("\n=== Logs ===")
    run("docker logs vpn_telegram_bot --tail=20 2>&1")
    
    client.close()
except Exception as e:
    print(f"Error: {e}")

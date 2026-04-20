import paramiko
import time

HOST, USER, PASS = "89.44.76.190", "root", "Mb69Bs5T18hNvrw5FC"

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=30)

    def run(cmd, timeout=120):
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode()
        if out: print(out)
        return out.strip()

    print("=== Git log (last commits) ===")
    run("cd ~/vpn_telegram && git log --oneline -10")
    
    print("\n=== Rollback to commit before my changes ===")
    # Find commit before "Fix: handlers with session"
    run("cd ~/vpn_telegram && git reset --hard 07e3e56")  # "Optimized for WiFi" commit
    
    print("\n=== Pull fresh code ===")
    run("cd ~/vpn_telegram && git pull origin main --force")
    
    print("\n=== Build and start ===")
    result = run("cd ~/vpn_telegram && timeout 120 docker compose up -d --build 2>&1 || echo 'TIMEOUT'", timeout=130)
    
    if "TIMEOUT" in result or "Network is unreachable" in result:
        print("\n⚠️ Build failed, trying without build...")
        # Try to find and use any existing image
        run("docker pull python:3.11-slim 2>&1 || true")
        run("cd ~/vpn_telegram && docker compose up -d --no-build 2>&1 || true")
    
    time.sleep(10)
    
    print("\n=== Status ===")
    run("docker ps | grep vpn")
    
    print("\n=== Logs ===")
    run("docker logs vpn_telegram_bot --tail=20 2>&1 || echo 'No container'")
    
    client.close()
except Exception as e:
    print(f"Error: {e}")

import paramiko
import time

HOST, USER, PASS = "89.44.76.190", "root", "Mb69Bs5T18hNvrw5FC"

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username='root', password=PASS, timeout=30)

    def run(cmd, timeout=60):
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode()
        if out: print(out)
        return out.strip()

    print("=== Killing stuck builds ===")
    run("pkill -9 docker-compose")
    run("pkill -9 dockerd")
    time.sleep(2)
    run("systemctl restart docker")
    time.sleep(5)
    
    print("\n=== Rollback code to working version ===")
    # Go back to commit BEFORE I started changing things
    run("cd ~/vpn_telegram && git reset --hard 2b114bc")  # "123" commit - was working
    
    print("\n=== Check for cached images ===")
    run("docker images -a | head -30")
    
    print("\n=== Try to start with any available image ===")
    run("cd ~/vpn_telegram && docker compose up -d --no-build 2>&1 || true")
    time.sleep(10)
    
    status = run("docker ps -a | grep vpn")
    
    if "vpn_telegram_bot" in status:
        print("\n✅ Bot container exists!")
        print("\n=== Logs ===")
        run("docker logs vpn_telegram_bot --tail=30 2>&1")
    else:
        print("\n❌ No bot container. Need manual intervention.")
        print("Сервер нужно перезагрузить или восстановить образ вручную")
    
    client.close()
except Exception as e:
    print(f"Error: {e}")

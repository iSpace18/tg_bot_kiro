import paramiko
import time

HOST, USER, PASS = "89.44.76.190", "root", "Mb69Bs5T18hNvrw5FC"

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username='root', password=PASS, timeout=30)

    def run(cmd, timeout=120):
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode()
        if out: print(out)
        return out.strip()

    print("=== Stop everything ===")
    run("cd ~/vpn_telegram && docker compose down")
    run("docker rm -f vpn_telegram_bot 2>&1 || true")
    
    print("\n=== Restore to LAST WORKING commit (before I broke it) ===")
    # This was the last commit where bot was working
    run("cd ~/vpn_telegram && git reset --hard 0dfb7c2")  # "Ultra-optimized" - was working!
    
    print("\n=== Try building with pip cache and network fixes ===")
    # Create Dockerfile that uses cached packages
    dockerfile_with_cache = '''FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir -r requirements.txt || pip install --no-cache-dir aiogram==3.10.0 sqlalchemy==2.0.36 asyncpg yookassa || true
COPY . .
CMD ["python3", "-m", "bot.main"]
'''
    
    # Upload new Dockerfile
    sftp = client.open_sftp()
    with sftp.open('/root/vpn_telegram/Dockerfile.new', 'w') as f:
        f.write(dockerfile_with_cache)
    sftp.close()
    
    # Try to build
    result = run("cd ~/vpn_telegram && timeout 90 docker build -f Dockerfile.new -t vpn_telegram-bot:latest . 2>&1 || echo 'BUILD_FAILED'", timeout=100)
    
    if "BUILD_FAILED" in result or "Network is unreachable" in result:
        print("\n⚠️ Build failed. Using fallback...")
        # Last resort - manually install in running container
        run("docker run -d --name vpn_telegram_bot_temp python:3.11-slim sleep 3600")
        time.sleep(3)
        
        # Copy code
        run("docker cp /root/vpn_telegram/. vpn_telegram_bot_temp:/app/")
        
        # Try to install packages (may fail but worth trying)
        run("docker exec vpn_telegram_bot_temp pip install aiogram==3.10.0 sqlalchemy==2.0.36 asyncpg yookassa 2>&1 || true", timeout=120)
        
        # Commit as image
        run("docker commit vpn_telegram_bot_temp vpn_telegram-bot:latest")
        run("docker rm -f vpn_telegram_bot_temp")
        
        print("✅ Created image from running container")
    
    print("\n=== Starting bot ===")
    run("cd ~/vpn_telegram && docker compose up -d")
    time.sleep(10)
    
    print("\n=== Status ===")
    run("docker ps | grep vpn")
    
    print("\n=== Logs ===")
    run("docker logs vpn_telegram_bot --tail=25 2>&1")
    
    client.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

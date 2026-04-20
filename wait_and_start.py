import paramiko
import time

HOST, USER, PASS = "89.44.76.190", "root", "Mb69Bs5T18hNvrw5FC"

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=30)

    def run(cmd, timeout=30):
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode()
        return out.strip()

    print("Waiting for build to complete...")
    
    for i in range(20):  # Wait up to 10 minutes
        time.sleep(30)
        
        # Check if image exists
        images = run("docker images | grep vpn_telegram-bot")
        if "vpn_telegram-bot" in images:
            print(f"\n✅ Image ready!")
            break
        
        print(f"Still building... ({i*30}s)")
    
    # Start bot
    print("\n=== Starting bot ===")
    run("cd ~/vpn_telegram && docker compose up -d")
    time.sleep(10)
    
    print("\n=== Status ===")
    print(run("docker ps | grep vpn"))
    
    print("\n=== Logs ===")
    print(run("docker logs vpn_telegram_bot --tail=20 2>&1"))
    
    print("\n✅ Done! Try buttons now.")
    
    client.close()
except Exception as e:
    print(f"Error: {e}")

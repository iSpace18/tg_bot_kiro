import paramiko

HOST = "89.44.76.190"
USER = "root"
PASS = "Mb69Bs5T18hNvrw5FC"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=30)

def run(cmd, timeout=60):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out)
    if err and "warning" not in err.lower():
        print("STDERR:", err)
    return out.strip()

print("=== Check current bot logs ===")
run("docker logs vpn_telegram_bot --tail=200 2>&1 | grep -A 5 -B 5 'Error\\|Exception\\|Traceback' | tail -100")

print("\n=== Check all handler files ===")
for handler in ['start', 'payment', 'admin', 'profile', 'referral']:
    print(f"\n=== {handler}.py first 30 lines ===")
    run(f"head -30 /root/vpn_telegram/bot/handlers/{handler}.py")

client.close()
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

print("=== Check referral.py on host ===")
run("cat /root/vpn_telegram/bot/handlers/referral.py")

print("\n=== Check referral.py in container ===")
run("docker exec vpn_telegram_bot cat /app/bot/handlers/referral.py")

print("\n=== Force remove Python cache ===")
run("docker exec vpn_telegram_bot find /app -name '*.pyc' -delete")
run("docker exec vpn_telegram_bot find /app -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true")

client.close()
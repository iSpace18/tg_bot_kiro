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

print("=== Check payment_service.py in container ===")
run("docker exec vpn_telegram_bot cat /app/bot/services/payment_service.py")

print("\\n=== Check payment.py yookassa handler ===")
run("docker exec vpn_telegram_bot grep -A 20 'pay_yookassa' /app/bot/handlers/payment.py | head -25")

client.close()
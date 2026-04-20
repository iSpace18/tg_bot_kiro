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

print("=== Check keyboards/main.py in container ===")
run("docker exec vpn_telegram_bot cat /app/bot/keyboards/main.py")

print("\n=== Try to import in container ===")
run("docker exec vpn_telegram_bot python -c 'from bot.keyboards.main import payment_method_keyboard; print(\"OK\")'")

client.close()
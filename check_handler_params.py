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

print("=== Check start handler signature ===")
run("grep -n 'def cmd_start' /root/vpn_telegram/bot/handlers/start.py")

print("\n=== Check payment handler signature ===")
run("grep -n 'def buy_vpn' /root/vpn_telegram/bot/handlers/payment.py")

print("\n=== Check admin handler signature ===")
run("grep -n 'def admin_panel' /root/vpn_telegram/bot/handlers/admin.py")

client.close()
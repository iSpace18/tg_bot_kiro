import paramiko

HOST = "89.44.76.190"
USER = "root"
PASS = "Mb69Bs5T18hNvrw5FC"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=30)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out)
    if err:
        print("STDERR:", err)
    return out.strip()

print("=== Check Docker images ===")
run("docker images | grep vpn")

print("\n=== Check network connectivity ===")
run("ping -c 3 8.8.8.8")

print("\n=== Check DNS ===")
run("nslookup pypi.org")

print("\n=== Check if bot files exist ===")
run("ls -la ~/vpn_telegram/bot/")

client.close()

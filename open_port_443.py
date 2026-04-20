import paramiko
import json
import time

HOST, USER, PASS = "89.44.76.190", "root", "Mb69Bs5T18hNvrw5FC"

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=30)

    def run(cmd, timeout=30):
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode()
        err = stderr.read().decode()
        if out: print(out)
        if err and 'warning' not in err.lower(): print(f"Error: {err}")
        return out.strip()

    print("=== Checking Firewall ===")
    
    # Check if ufw is active
    ufw_status = run("ufw status 2>&1 || echo 'ufw not found'")
    
    if "inactive" in ufw_status.lower() or "not found" in ufw_status.lower():
        print("UFW is not active or not installed")
        
        # Check iptables
        print("\n=== Checking iptables ===")
        iptables = run("iptables -L -n | grep 443 || echo 'No 443 rules'")
        
        print("\n=== Opening port 443 ===")
        # Add iptables rule to allow 443
        run("iptables -I INPUT -p tcp --dport 443 -j ACCEPT")
        run("iptables -I INPUT -p udp --dport 443 -j ACCEPT")
        
        # Save iptables rules
        run("iptables-save > /etc/iptables/rules.v4 2>&1 || netfilter-persistent save 2>&1 || echo 'Saved to memory only'")
        
        print("✅ Port 443 opened in iptables")
    else:
        print("UFW is active")
        print("\n=== Opening port 443 in UFW ===")
        run("ufw allow 443/tcp")
        run("ufw allow 443/udp")
        print("✅ Port 443 opened in UFW")
    
    # Check if port 443 is already in use
    print("\n=== Checking if port 443 is in use ===")
    port_check = run("netstat -tlnp | grep :443 || ss -tlnp | grep :443 || echo 'Port 443 is free'")
    
    if "443" in port_check and "free" not in port_check:
        print("⚠️ Port 443 is already in use by another service")
        print("Let's use port 2053 instead (Cloudflare port, good for mobile)")
        
        # Change back to 2053
        run("sqlite3 /etc/x-ui/x-ui.db \"UPDATE inbounds SET port = 2053 WHERE protocol='vless';\"")
        print("✅ Changed to port 2053")
        
        final_port = 2053
    else:
        print("✅ Port 443 is available")
        final_port = 443
    
    print("\n=== Restarting Xray ===")
    run("pkill -SIGHUP xray")
    time.sleep(2)
    
    # Verify xray is listening
    print("\n=== Verifying Xray is listening ===")
    listen_check = run(f"netstat -tlnp | grep :{final_port} || ss -tlnp | grep :{final_port} || echo 'Not listening yet'")
    
    if str(final_port) in listen_check:
        print(f"✅ Xray is listening on port {final_port}")
    else:
        print(f"⚠️ Xray might not be listening on port {final_port} yet")
        print("Waiting 5 seconds...")
        time.sleep(5)
        listen_check = run(f"netstat -tlnp | grep :{final_port} || ss -tlnp | grep :{final_port}")
    
    # Reset trial
    print("\n=== Resetting Trial ===")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"UPDATE users SET trial_used = 0 WHERE telegram_id = 1658346274;\"")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"DELETE FROM vpn_keys;\"")
    
    # Restart bot
    print("\n=== Restarting Bot ===")
    run("cd ~/vpn_telegram && docker compose restart", timeout=60)
    time.sleep(8)
    
    print(f"\n✅ Configuration complete!")
    print(f"\n📱 Final settings:")
    print(f"   - Port: {final_port}")
    print(f"   - Security: Reality")
    print(f"   - Target: www.microsoft.com")
    print(f"   - Firewall: Port opened")
    print(f"\n🔑 Get a new trial key and test on mobile network")
    
    # Test port from outside
    print(f"\n=== Testing port {final_port} from outside ===")
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((HOST, final_port))
        sock.close()
        if result == 0:
            print(f"✅ Port {final_port} is accessible from outside")
        else:
            print(f"❌ Port {final_port} is NOT accessible from outside")
            print("This might be a VPS provider firewall issue")
    except Exception as e:
        print(f"Test error: {e}")

    client.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

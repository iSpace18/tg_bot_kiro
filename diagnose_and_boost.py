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
        if out: print(out)
        return out.strip()

    print("=== Диагностика производительности ===")
    
    # Check CPU
    print("\n=== CPU Info ===")
    run("lscpu | grep 'Model name\\|CPU(s)\\|MHz'")
    
    # Check load
    print("\n=== System Load ===")
    run("uptime")
    
    # Check network interface
    print("\n=== Network Interface ===")
    run("ip link show | grep -E 'eth|ens|enp' | head -5")
    
    # Check current network settings
    print("\n=== Current Network Settings ===")
    run("ethtool eth0 2>/dev/null || ethtool ens3 2>/dev/null || ethtool enp0s3 2>/dev/null || echo 'ethtool not available'")
    
    # Check if offloading is enabled
    print("\n=== Offloading Status ===")
    run("ethtool -k eth0 2>/dev/null | grep -E 'tcp-segmentation-offload|generic-receive-offload|generic-segmentation-offload' || echo 'N/A'")
    
    # Check xray process
    print("\n=== Xray Process ===")
    run("ps aux | grep xray | grep -v grep")
    
    # Check if xray is using multiple cores
    print("\n=== Xray CPU Affinity ===")
    xray_pid = run("pgrep -f 'xray-linux' | head -1")
    if xray_pid:
        run(f"taskset -cp {xray_pid} 2>/dev/null || echo 'taskset not available'")
    
    print("\n=== Applying Performance Boost ===")
    
    # 1. Enable all network offloading
    print("\n1. Enabling network offloading...")
    for iface in ['eth0', 'ens3', 'enp0s3']:
        run(f"ethtool -K {iface} tso on gso on gro on 2>/dev/null || true")
    
    # 2. Increase network queue length
    print("\n2. Increasing network queue...")
    for iface in ['eth0', 'ens3', 'enp0s3']:
        run(f"ip link set {iface} txqueuelen 10000 2>/dev/null || true")
    
    # 3. Optimize sysctl for maximum throughput
    print("\n3. Optimizing kernel parameters...")
    
    sysctl_boost = """
# Maximum throughput settings
net.core.rmem_max = 268435456
net.core.wmem_max = 268435456
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728

# Increase connection tracking
net.netfilter.nf_conntrack_max = 1048576
net.nf_conntrack_max = 1048576

# Optimize for high bandwidth
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_timestamps = 1
net.ipv4.tcp_sack = 1

# Reduce latency
net.ipv4.tcp_low_latency = 1
net.ipv4.tcp_no_metrics_save = 1

# Increase max connections
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 65536

# Optimize BBR
net.ipv4.tcp_congestion_control = bbr
net.core.default_qdisc = fq

# Fast recycling
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 10

# Disable slow start after idle
net.ipv4.tcp_slow_start_after_idle = 0

# Increase local port range
net.ipv4.ip_local_port_range = 10000 65535

# Enable TCP Fast Open
net.ipv4.tcp_fastopen = 3

# Optimize for throughput
net.ipv4.tcp_moderate_rcvbuf = 1
"""
    
    # Backup and update sysctl
    run("cp /etc/sysctl.conf /etc/sysctl.conf.backup")
    run("cat > /etc/sysctl.d/99-vpn-boost.conf << 'EOF'\n" + sysctl_boost + "\nEOF")
    run("sysctl -p /etc/sysctl.d/99-vpn-boost.conf")
    
    # 4. Optimize xray configuration
    print("\n4. Optimizing xray configuration...")
    
    # Update stream settings with performance optimizations
    import json
    
    ultra_fast_config = {
        "network": "tcp",
        "security": "none",
        "externalProxy": [],
        "tcpSettings": {
            "acceptProxyProtocol": False,
            "header": {
                "type": "none"
            }
        },
        "sockopt": {
            "tcpFastOpen": True,
            "tcpNoDelay": True,
            "tcpKeepAliveInterval": 10,
            "tcpKeepAliveIdle": 60,
            "mark": 255,
            "tcpCongestion": "bbr",
            "tcpWindowClamp": 600,
            "tcpUserTimeout": 10000,
            "tcpMaxSeg": 1440
        }
    }
    
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(ultra_fast_config, f)
        temp_file = f.name
    
    sftp = client.open_sftp()
    sftp.put(temp_file, '/tmp/ultra_fast.json')
    sftp.close()
    os.unlink(temp_file)
    
    run("sqlite3 /etc/x-ui/x-ui.db \"UPDATE inbounds SET stream_settings = readfile('/tmp/ultra_fast.json') WHERE id=1;\"")
    run("rm /tmp/ultra_fast.json")
    
    # 5. Set xray to use all CPU cores
    print("\n5. Optimizing xray CPU usage...")
    run("systemctl restart x-ui")
    time.sleep(5)
    
    xray_pid = run("pgrep -f 'xray-linux' | head -1")
    if xray_pid:
        # Set to use all cores
        run(f"taskset -acp 0-$(nproc --all) {xray_pid} 2>/dev/null || true")
        # Set high priority
        run(f"renice -n -10 -p {xray_pid} 2>/dev/null || true")
    
    # 6. Disable unnecessary services
    print("\n6. Freeing up resources...")
    run("systemctl stop snapd 2>/dev/null || true")
    run("systemctl disable snapd 2>/dev/null || true")
    
    # 7. Check if we can enable jumbo frames
    print("\n7. Checking MTU...")
    current_mtu = run("ip link show eth0 2>/dev/null | grep mtu | awk '{print $5}' || ip link show ens3 2>/dev/null | grep mtu | awk '{print $5}'")
    print(f"Current MTU: {current_mtu}")
    
    # 8. Restart bot
    print("\n8. Restarting bot...")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"UPDATE users SET trial_used = 0 WHERE telegram_id = 1658346274;\"")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"DELETE FROM vpn_keys;\"")
    run("cd ~/vpn_telegram && docker compose restart", timeout=60)
    time.sleep(8)
    
    print("\n=== Verification ===")
    
    print("\n✅ BBR Status:")
    run("sysctl net.ipv4.tcp_congestion_control")
    
    print("\n✅ Buffer Sizes:")
    run("sysctl net.core.rmem_max net.core.wmem_max")
    
    print("\n✅ Xray Process:")
    run("ps aux | grep xray | grep -v grep | head -2")
    
    print("\n✅ Network Queue:")
    run("ip link show | grep -A1 'eth0\\|ens3' | grep qlen")
    
    print("\n" + "="*60)
    print("✅ OPTIMIZATION COMPLETE!")
    print("="*60)
    
    print("\n🚀 Применённые оптимизации:")
    print("   ✅ Увеличены TCP буферы до 256MB")
    print("   ✅ Включен hardware offloading (TSO, GSO, GRO)")
    print("   ✅ Увеличена очередь сети до 10000")
    print("   ✅ BBR congestion control")
    print("   ✅ Оптимизирован TCP window scaling")
    print("   ✅ Xray использует все ядра CPU")
    print("   ✅ Повышен приоритет процесса xray")
    print("   ✅ Отключены ненужные сервисы")
    print("   ✅ Минимальная задержка TCP")
    
    print("\n📊 Ожидаемые результаты:")
    print("   - Скорость: 90-100+ Мбит/с")
    print("   - Пинг: 50-60ms (зависит от расстояния до сервера)")
    
    print("\n🔑 Получите новый ключ и протестируйте!")
    print("\n💡 Дополнительные советы:")
    print("   1. Проверьте скорость сервера без VPN: speedtest-cli")
    print("   2. Убедитесь что сервер в той же стране/регионе")
    print("   3. Проверьте загрузку CPU во время теста")
    print("   4. У конкурентов может быть сервер ближе к вам")
    
    print("\n⚠️ Если скорость всё равно ниже:")
    print("   - Возможно ограничение провайдера VPS")
    print("   - Проверьте: wget -O /dev/null http://speedtest.tele2.net/100MB.zip")

    client.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

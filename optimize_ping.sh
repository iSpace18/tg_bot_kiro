#!/bin/bash

echo "=== Оптимизация для стабильного пинга ==="
echo ""

# 1. Optimize sysctl for low latency
echo "1. Применение оптимизаций sysctl для низкой задержки..."

cat > /etc/sysctl.d/99-vpn-low-latency.conf << 'EOF'
# TCP optimization for low latency
net.ipv4.tcp_low_latency = 1
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_no_metrics_save = 1
net.ipv4.tcp_moderate_rcvbuf = 1

# Reduce TCP retransmission timeout
net.ipv4.tcp_retries2 = 8
net.ipv4.tcp_orphan_retries = 3

# BBR congestion control (already set but ensure it's active)
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr

# Increase buffer sizes for better throughput
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 67108864
net.ipv4.tcp_wmem = 4096 65536 67108864

# Reduce TIME_WAIT sockets
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_tw_reuse = 1

# Enable TCP window scaling
net.ipv4.tcp_window_scaling = 1

# Disable slow start after idle
net.ipv4.tcp_slow_start_after_idle = 0

# MTU probing
net.ipv4.tcp_mtu_probing = 1

# Reduce keepalive time
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 10
net.ipv4.tcp_keepalive_probes = 6
EOF

sysctl -p /etc/sysctl.d/99-vpn-low-latency.conf > /dev/null 2>&1
echo "   ✅ Sysctl оптимизации применены"

# 2. Optimize Xray config for low latency
echo ""
echo "2. Оптимизация конфигурации Xray..."

python3 << 'PYTHON_SCRIPT'
import json

CONFIG_PATH = "/usr/local/x-ui/bin/config.json"

with open(CONFIG_PATH, 'r') as f:
    config = json.load(f)

# Optimize policy for low latency
if 'policy' not in config:
    config['policy'] = {}

config['policy']['levels'] = {
    "0": {
        "statsUserDownlink": True,
        "statsUserUplink": True,
        "handshake": 2,  # Reduced from 4
        "connIdle": 120,  # Reduced from 300
        "uplinkOnly": 0,
        "downlinkOnly": 0,
        "bufferSize": 256  # Reduced from 512 for lower latency
    }
}

# Optimize inbound sockopt
for inbound in config.get('inbounds', []):
    if inbound.get('protocol') == 'vless':
        if 'streamSettings' not in inbound:
            inbound['streamSettings'] = {}
        
        if 'sockopt' not in inbound['streamSettings']:
            inbound['streamSettings']['sockopt'] = {}
        
        # Optimize for low latency
        inbound['streamSettings']['sockopt'].update({
            "mark": 255,
            "tcpCongestion": "bbr",
            "tcpFastOpen": True,
            "tcpKeepAliveIdle": 60,  # Reduced from 100
            "tcpKeepAliveInterval": 10,
            "tcpNoDelay": True,
            "tcpMptcp": False,
            "tcpUserTimeout": 10000  # 10 seconds
        })

# Optimize outbound
for outbound in config.get('outbounds', []):
    if outbound.get('protocol') == 'freedom':
        if 'streamSettings' not in outbound:
            outbound['streamSettings'] = {}
        
        if 'sockopt' not in outbound['streamSettings']:
            outbound['streamSettings']['sockopt'] = {}
        
        outbound['streamSettings']['sockopt'].update({
            "tcpFastOpen": True,
            "tcpNoDelay": True,
            "tcpKeepAliveIdle": 60,
            "tcpKeepAliveInterval": 10
        })

with open(CONFIG_PATH, 'w') as f:
    json.dump(config, f, indent=2)

print("   ✅ Xray конфигурация оптимизирована")
PYTHON_SCRIPT

# 3. Optimize network interface
echo ""
echo "3. Оптимизация сетевого интерфейса..."

# Get primary network interface
IFACE=$(ip route | grep default | awk '{print $5}' | head -1)

if [ -n "$IFACE" ]; then
    # Disable offloading features that can cause latency spikes
    ethtool -K $IFACE tso off gso off gro off 2>/dev/null || true
    echo "   ✅ Отключены offloading функции на $IFACE"
else
    echo "   ⚠️  Не удалось определить сетевой интерфейс"
fi

# 4. Set CPU governor to performance
echo ""
echo "4. Установка CPU governor на performance..."

if [ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
    for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
        echo performance > $cpu 2>/dev/null || true
    done
    echo "   ✅ CPU governor установлен на performance"
else
    echo "   ℹ️  CPU frequency scaling недоступен"
fi

# 5. Optimize IRQ affinity
echo ""
echo "5. Оптимизация IRQ affinity..."

# This helps distribute network interrupts across CPUs
if command -v irqbalance &> /dev/null; then
    systemctl enable irqbalance 2>/dev/null || true
    systemctl start irqbalance 2>/dev/null || true
    echo "   ✅ IRQ balance включен"
else
    echo "   ℹ️  irqbalance не установлен"
fi

echo ""
echo "=== Оптимизация завершена ==="
echo ""
echo "Перезапустите x-ui для применения изменений:"
echo "  systemctl restart x-ui"

#!/bin/bash
# VPN Diagnostic Script

echo "=========================================="
echo "VPN DIAGNOSTIC REPORT"
echo "=========================================="
echo ""

echo "1. XRAY PROCESS STATUS"
echo "----------------------------------------"
if ps aux | grep -v grep | grep xray > /dev/null; then
    echo "✅ Xray is running"
    ps aux | grep -v grep | grep xray | head -1
else
    echo "❌ Xray is NOT running"
fi
echo ""

echo "2. PORT 443 STATUS"
echo "----------------------------------------"
if ss -tlnp | grep :443 > /dev/null; then
    echo "✅ Port 443 is listening"
    ss -tlnp | grep :443
else
    echo "❌ Port 443 is NOT listening"
fi
echo ""

echo "3. REALITY CONFIGURATION"
echo "----------------------------------------"
python3 << 'EOF'
import json
try:
    with open('/usr/local/x-ui/bin/config.json', 'r') as f:
        config = json.load(f)
    
    vless_inbound = [i for i in config['inbounds'] if i.get('protocol') == 'vless'][0]
    reality = vless_inbound['streamSettings']['realitySettings']
    
    print(f"✅ Reality configuration found")
    print(f"   dest: {reality['dest']}")
    print(f"   serverNames: {reality['serverNames']}")
    print(f"   privateKey: {reality['privateKey'][:20]}...")
    
    # Check if djanvpn.ru is in serverNames
    if 'djanvpn.ru' in reality['serverNames']:
        print(f"   ✅ djanvpn.ru is in serverNames")
    else:
        print(f"   ❌ djanvpn.ru is NOT in serverNames")
        
except Exception as e:
    print(f"❌ Error reading config: {e}")
EOF
echo ""

echo "4. DOMAIN RESOLUTION"
echo "----------------------------------------"
if nslookup djanvpn.ru > /dev/null 2>&1; then
    echo "✅ djanvpn.ru resolves"
    nslookup djanvpn.ru | grep -A2 "Name:" | tail -3
else
    echo "❌ djanvpn.ru does NOT resolve"
fi
echo ""

echo "5. ACTIVE CLIENTS"
echo "----------------------------------------"
python3 << 'EOF'
import json
try:
    with open('/usr/local/x-ui/bin/config.json', 'r') as f:
        config = json.load(f)
    
    vless_inbound = [i for i in config['inbounds'] if i.get('protocol') == 'vless'][0]
    clients = vless_inbound['settings'].get('clients', [])
    
    print(f"Total clients: {len(clients)}")
    for client in clients:
        print(f"   - {client['email']} (UUID: {client['id'][:8]}...)")
        
except Exception as e:
    print(f"❌ Error: {e}")
EOF
echo ""

echo "6. BOT STATUS"
echo "----------------------------------------"
if docker ps | grep vpn_telegram_bot > /dev/null; then
    echo "✅ Bot container is running"
    docker ps | grep vpn_telegram_bot
else
    echo "❌ Bot container is NOT running"
fi
echo ""

echo "7. FIREWALL STATUS"
echo "----------------------------------------"
if command -v ufw > /dev/null; then
    echo "UFW status:"
    ufw status | grep 443 || echo "   Port 443 not explicitly configured"
elif command -v iptables > /dev/null; then
    echo "iptables rules for port 443:"
    iptables -L -n | grep 443 || echo "   No specific rules for port 443"
else
    echo "   No firewall detected"
fi
echo ""

echo "8. XRAY LOGS (last 10 lines)"
echo "----------------------------------------"
if [ -f /usr/local/x-ui/error.log ]; then
    tail -10 /usr/local/x-ui/error.log
else
    echo "   No error log found"
fi
echo ""

echo "=========================================="
echo "DIAGNOSTIC COMPLETE"
echo "=========================================="

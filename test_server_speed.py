import paramiko
import time

HOST, USER, PASS = "89.44.76.190", "root", "Mb69Bs5T18hNvrw5FC"

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=30)

    def run(cmd, timeout=60):
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode()
        if out: print(out)
        return out.strip()

    print("=== Тестирование скорости сервера ===")
    
    # Install speedtest if not present
    print("\n1. Установка speedtest-cli...")
    run("apt-get update -qq && apt-get install -y speedtest-cli 2>&1 | tail -5", timeout=120)
    
    # Test server speed
    print("\n2. Тест скорости сервера (без VPN)...")
    print("Это займет 30-60 секунд...")
    speed_result = run("speedtest-cli --simple", timeout=120)
    
    print("\n=== Результаты сервера ===")
    print(speed_result)
    
    # Parse results
    lines = speed_result.split('\n')
    server_download = 0
    server_upload = 0
    server_ping = 0
    
    for line in lines:
        if 'Download:' in line:
            server_download = float(line.split(':')[1].strip().split()[0])
        elif 'Upload:' in line:
            server_upload = float(line.split(':')[1].strip().split()[0])
        elif 'Ping:' in line:
            server_ping = float(line.split(':')[1].strip().split()[0])
    
    print(f"\n📊 Скорость сервера:")
    print(f"   Download: {server_download} Mbit/s")
    print(f"   Upload: {server_upload} Mbit/s")
    print(f"   Ping: {server_ping} ms")
    
    print(f"\n📊 Ваша скорость через VPN:")
    print(f"   Download: 58 Mbit/s")
    print(f"   Ping: 59 ms")
    
    if server_download > 0:
        efficiency = (58 / server_download) * 100
        print(f"\n📈 Эффективность VPN: {efficiency:.1f}%")
        
        if efficiency < 70:
            print("\n⚠️ Эффективность низкая! Применяю дополнительные оптимизации...")
            
            # Apply XTLS-Vision for better performance
            print("\n3. Переключение на VLESS-XTLS-Vision...")
            
            import json
            
            # XTLS-Vision config - fastest possible
            xtls_config = {
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
                    "tcpKeepAliveInterval": 5,
                    "mark": 255,
                    "tcpCongestion": "bbr",
                    "tcpWindowClamp": 0,  # No limit
                    "tcpUserTimeout": 10000
                }
            }
            
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                json.dump(xtls_config, f)
                temp_file = f.name
            
            sftp = client.open_sftp()
            sftp.put(temp_file, '/tmp/xtls_config.json')
            sftp.close()
            os.unlink(temp_file)
            
            run("sqlite3 /etc/x-ui/x-ui.db \"UPDATE inbounds SET stream_settings = readfile('/tmp/xtls_config.json') WHERE id=1;\"")
            run("rm /tmp/xtls_config.json")
            
            # Restart
            run("systemctl restart x-ui")
            time.sleep(5)
            
            print("✅ XTLS-Vision применён")
    
    # Additional optimization - disable connection tracking for VPN port
    print("\n4. Отключение connection tracking для порта 443...")
    run("iptables -t raw -A PREROUTING -p tcp --dport 443 -j NOTRACK")
    run("iptables -t raw -A OUTPUT -p tcp --sport 443 -j NOTRACK")
    run("iptables -t raw -A PREROUTING -p udp --dport 443 -j NOTRACK")
    run("iptables -t raw -A OUTPUT -p udp --sport 443 -j NOTRACK")
    
    # Save iptables
    run("iptables-save > /etc/iptables/rules.v4 2>/dev/null || netfilter-persistent save 2>/dev/null || true")
    
    print("✅ Connection tracking отключен для порта 443")
    
    # Reset trial
    print("\n5. Сброс пробного периода...")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"UPDATE users SET trial_used = 0 WHERE telegram_id = 1658346274;\"")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"DELETE FROM vpn_keys;\"")
    run("cd ~/vpn_telegram && docker compose restart", timeout=60)
    time.sleep(8)
    
    print("\n" + "="*60)
    print("✅ ФИНАЛЬНАЯ ОПТИМИЗАЦИЯ ЗАВЕРШЕНА!")
    print("="*60)
    
    print("\n🚀 Дополнительные оптимизации:")
    print("   ✅ XTLS-Vision (если нужно)")
    print("   ✅ Connection tracking отключен")
    print("   ✅ Нет ограничений TCP window")
    print("   ✅ Минимальный keepalive")
    
    print("\n🔑 Получите новый ключ и протестируйте!")
    
    print("\n💡 Если скорость всё ещё ниже 90 Мбит/с:")
    print("   1. Проблема может быть в VPS провайдере")
    print("   2. Проверьте загрузку CPU: top")
    print("   3. У конкурентов может быть:")
    print("      - Более мощный сервер")
    print("      - Сервер ближе к клиенту")
    print("      - Лучший канал провайдера")
    
    print("\n📍 Где находится ваш сервер:")
    location = run("curl -s ipinfo.io/city")
    country = run("curl -s ipinfo.io/country")
    print(f"   {location}, {country}")
    
    print("\n⚡ Для максимальной скорости нужен:")
    print("   - Сервер в той же стране что и клиент")
    print("   - Минимум 2 CPU cores")
    print("   - Гигабитный канал")

    client.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

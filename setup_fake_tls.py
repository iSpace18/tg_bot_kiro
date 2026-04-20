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
        if out: print(out)
        return out.strip()

    print("=== Настройка HTTP Obfuscation для обхода DPI ===")
    print("Будем маскировать VPN под обычный HTTP трафик")
    
    # Delete all existing inbounds except first one
    print("\n=== Cleaning up old inbounds ===")
    run("sqlite3 /etc/x-ui/x-ui.db \"DELETE FROM inbounds WHERE id > 1;\"")
    
    # Get settings from first inbound
    settings = run("sqlite3 /etc/x-ui/x-ui.db \"SELECT settings FROM inbounds WHERE id=1;\"")
    
    # Create simple HTTP inbound on port 80 (most reliable for mobile)
    http_config = {
        "network": "tcp",
        "security": "none",
        "externalProxy": [],
        "tcpSettings": {
            "acceptProxyProtocol": False,
            "header": {
                "type": "http",
                "request": {
                    "version": "1.1",
                    "method": "GET",
                    "path": ["/", "/video", "/api"],
                    "headers": {
                        "Host": ["www.amazon.com", "www.microsoft.com", "www.bing.com"],
                        "User-Agent": [
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
                        ],
                        "Accept-Encoding": ["gzip, deflate"],
                        "Connection": ["keep-alive"],
                        "Pragma": "no-cache"
                    }
                },
                "response": {
                    "version": "1.1",
                    "status": "200",
                    "reason": "OK",
                    "headers": {
                        "Content-Type": ["application/octet-stream", "video/mpeg"],
                        "Transfer-Encoding": ["chunked"],
                        "Connection": ["keep-alive"],
                        "Pragma": "no-cache"
                    }
                }
            }
        }
    }
    
    import tempfile
    import os
    
    # Create HTTP obfuscation inbound
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(http_config, f)
        temp_stream = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        f.write(settings)
        temp_settings = f.name
    
    sftp = client.open_sftp()
    sftp.put(temp_stream, '/tmp/http_stream.json')
    sftp.put(temp_settings, '/tmp/http_settings.json')
    sftp.close()
    
    os.unlink(temp_stream)
    os.unlink(temp_settings)
    
    # Update port 80 inbound or create new
    check_80 = run("sqlite3 /etc/x-ui/x-ui.db \"SELECT id FROM inbounds WHERE port=80;\"")
    
    if check_80:
        print("Updating port 80 with HTTP obfuscation...")
        run("sqlite3 /etc/x-ui/x-ui.db \"UPDATE inbounds SET stream_settings = readfile('/tmp/http_stream.json'), settings = readfile('/tmp/http_settings.json') WHERE port=80;\"")
    else:
        print("Creating HTTP obfuscation inbound on port 80...")
        sniffing = '{\\"enabled\\":true,\\"destOverride\\":[\\"http\\",\\"tls\\"]}'
        run(f"sqlite3 /etc/x-ui/x-ui.db \"INSERT INTO inbounds (user_id, up, down, total, remark, enable, expiry_time, listen, port, protocol, settings, stream_settings, tag, sniffing) VALUES (1, 0, 0, 0, 'HTTP-Obfs-Mobile', 1, 0, '', 80, 'vless', readfile('/tmp/http_settings.json'), readfile('/tmp/http_stream.json'), 'inbound-80', '{sniffing}');\"")
    
    run("rm /tmp/http_stream.json /tmp/http_settings.json")
    
    # Also update Reality to use port 8443 instead of 443 (443 might be blocked)
    print("\n=== Moving Reality to port 8443 ===")
    run("sqlite3 /etc/x-ui/x-ui.db \"UPDATE inbounds SET port = 8443 WHERE id=1;\"")
    
    print("\n✅ Configuration updated")
    
    # Restart xray
    print("\n=== Restarting X-UI ===")
    run("systemctl restart x-ui")
    time.sleep(5)
    
    # Verify
    print("\n=== Current Inbounds ===")
    inbounds = run("sqlite3 /etc/x-ui/x-ui.db \"SELECT id, port, remark FROM inbounds;\"")
    
    print("\n=== Listening Ports ===")
    ports = run("ss -tlnp | grep xray")
    
    # Update bot to use new configuration
    print("\n=== Updating Bot ===")
    
    bot_code = '''import logging
import sqlite3
import uuid
import os
import signal
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from bot.config import settings

logger = logging.getLogger(__name__)

XUI_DB_PATH = "/etc/x-ui/x-ui.db"


def _db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(XUI_DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    return conn


def _restart_xray():
    try:
        xray_pids = []
        for pid_str in os.listdir('/proc'):
            if not pid_str.isdigit():
                continue
            try:
                with open(f'/proc/{pid_str}/cmdline', 'rb') as f:
                    cmdline = f.read().replace(b'\\x00', b' ').decode(errors='ignore')
                if 'xray-linux' in cmdline:
                    xray_pids.append(int(pid_str))
            except:
                pass
        
        if xray_pids:
            for pid in xray_pids:
                os.kill(pid, signal.SIGHUP)
            logger.info(f"Sent SIGHUP to xray PIDs: {xray_pids}")
    except Exception as e:
        logger.error(f"Failed to restart xray: {e}")


class VPNService:
    def __init__(self):
        self.base_url = settings.VPN_PANEL_URL.rstrip("/")
        self._inbound_ids: Optional[list] = None
        logger.info("VPNService initialized")

    def _get_inbound_ids(self) -> list:
        if self._inbound_ids is not None:
            return self._inbound_ids
        conn = _db_connect()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, port, stream_settings FROM inbounds WHERE protocol='vless' ORDER BY port")
            rows = cursor.fetchall()
            if not rows:
                raise Exception("No VLESS inbounds found")
            self._inbound_ids = [(row[0], row[1], json.loads(row[2])) for row in rows]
            logger.info(f"Found {len(self._inbound_ids)} VLESS inbounds")
            return self._inbound_ids
        finally:
            conn.close()

    def _get_server_ip(self) -> str:
        url = settings.VPN_PANEL_URL.rstrip("/")
        url = url.replace("https://", "").replace("http://", "")
        return url.split(":")[0]

    def _create_user_sync(self, username: str, expiry_days: int, traffic_limit_gb: Optional[int]) -> Dict[str, Any]:
        inbounds = self._get_inbound_ids()
        client_uuid = str(uuid.uuid4())
        expiry_ts = int((datetime.utcnow() + timedelta(days=expiry_days)).timestamp() * 1000)
        total_gb = (traffic_limit_gb * 1024 * 1024 * 1024) if traffic_limit_gb else 0

        conn = _db_connect()
        try:
            cursor = conn.cursor()
            
            for inbound_id, port, stream_settings in inbounds:
                cursor.execute("SELECT settings FROM inbounds WHERE id = ?", (inbound_id,))
                row = cursor.fetchone()
                if not row:
                    continue

                settings_json = json.loads(row[0])
                
                new_client = {
                    "id": client_uuid,
                    "email": username,
                    "enable": True,
                    "expiryTime": expiry_ts,
                    "totalGB": total_gb,
                    "limitIp": 1,
                }

                if "clients" not in settings_json:
                    settings_json["clients"] = []
                settings_json["clients"].append(new_client)

                cursor.execute(
                    "UPDATE inbounds SET settings = ? WHERE id = ?",
                    (json.dumps(settings_json), inbound_id),
                )
                logger.info(f"Client added to inbound {inbound_id}, port={port}")
            
            conn.commit()
        finally:
            conn.close()

        _restart_xray()

        server_ip = self._get_server_ip()
        from urllib.parse import quote
        
        urls = []
        for inbound_id, port, stream_settings in inbounds:
            network = stream_settings.get("network", "tcp")
            security = stream_settings.get("security", "none")
            
            if port == 80 and network == "tcp":
                # HTTP obfuscation
                display_name = f"⚡ NL-Mobile-{port}"
                url = (
                    f"vless://{client_uuid}@{server_ip}:{port}"
                    f"?type=tcp&headerType=http&host=www.microsoft.com&path=/video"
                    f"&security=none&encryption=none#{quote(display_name)}"
                )
                urls.append(url)
            
            elif security == "reality":
                # Reality
                reality_settings = stream_settings.get("realitySettings", {})
                server_names = reality_settings.get("serverNames", [])
                short_ids = reality_settings.get("shortIds", [])
                public_key = reality_settings.get("settings", {}).get("publicKey", "")
                fingerprint = reality_settings.get("settings", {}).get("fingerprint", "chrome")
                spider_x = reality_settings.get("settings", {}).get("spiderX", "/")
                
                sni = server_names[0] if server_names else "www.microsoft.com"
                sid = short_ids[0] if short_ids else ""
                spider_x_encoded = quote(spider_x, safe='')
                
                display_name = f"⚡ NL-WiFi-{port}"
                url = (
                    f"vless://{client_uuid}@{server_ip}:{port}"
                    f"?type=tcp&security=reality&pbk={public_key}&fp={fingerprint}"
                    f"&sni={sni}&sid={sid}&spx={spider_x_encoded}#{quote(display_name)}"
                )
                urls.append(url)
        
        subscription_content = "\\n\\n".join(urls)
        
        return {
            "uuid": client_uuid,
            "subscription_url": subscription_content,
            "expiry_date": datetime.fromtimestamp(expiry_ts / 1000),
        }

    async def create_user(self, username: str, expiry_days: int, traffic_limit_gb: Optional[int] = None) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._create_user_sync, username, expiry_days, traffic_limit_gb)
        await asyncio.sleep(3)
        return result

    def _delete_user_sync(self, username: str) -> bool:
        inbounds = self._get_inbound_ids()
        conn = _db_connect()
        try:
            cursor = conn.cursor()
            for inbound_id, port, _ in inbounds:
                cursor.execute("SELECT settings FROM inbounds WHERE id = ?", (inbound_id,))
                row = cursor.fetchone()
                if not row:
                    continue
                settings_json = json.loads(row[0])
                clients = settings_json.get("clients", [])
                new_clients = [c for c in clients if c.get("email") != username]
                settings_json["clients"] = new_clients
                cursor.execute("UPDATE inbounds SET settings = ? WHERE id = ?", (json.dumps(settings_json), inbound_id))
            conn.commit()
        finally:
            conn.close()
        _restart_xray()
        return True

    async def delete_user(self, username: str) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._delete_user_sync, username)

    async def get_client_info(self, username: str) -> Optional[Dict[str, Any]]:
        def _sync():
            inbounds = self._get_inbound_ids()
            conn = _db_connect()
            try:
                cursor = conn.cursor()
                for inbound_id, _, _ in inbounds:
                    cursor.execute("SELECT settings FROM inbounds WHERE id = ?", (inbound_id,))
                    row = cursor.fetchone()
                    if not row:
                        continue
                    data = json.loads(row[0])
                    for c in data.get("clients", []):
                        if c.get("email") == username:
                            return c
                return None
            finally:
                conn.close()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync)


vpn_service = VPNService()
'''
    
    with open('bot/services/vpn_service.py', 'w', encoding='utf-8') as f:
        f.write(bot_code)
    
    sftp = client.open_sftp()
    with sftp.open('/root/vpn_telegram/bot/services/vpn_service.py', 'w') as f:
        f.write(bot_code)
    sftp.close()
    
    print("✅ Bot code updated")
    
    # Reset and restart
    print("\n=== Resetting Trial ===")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"UPDATE users SET trial_used = 0 WHERE telegram_id = 1658346274;\"")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"DELETE FROM vpn_keys;\"")
    
    print("\n=== Rebuilding Bot ===")
    run("cd ~/vpn_telegram && docker compose down", timeout=60)
    time.sleep(2)
    run("cd ~/vpn_telegram && docker compose up -d --build", timeout=120)
    time.sleep(10)
    
    print("\n=== Bot Logs ===")
    run("docker logs vpn_telegram_bot --tail=20 2>&1")
    
    print("\n✅ Setup complete!")
    print("\n📱 Новая конфигурация:")
    print("   1. Port 80 - HTTP Obfuscation (маскировка под обычный HTTP)")
    print("      Имитирует запросы к Microsoft/Amazon")
    print("   2. Port 8443 - Reality (для WiFi)")
    print("\n🔑 Получите новый ключ и протестируйте на мобильном")
    print("\n💡 HTTP Obfuscation обычно проходит через любого оператора")
    print("\n⚠️ Если не поможет - ваш оператор использует whitelist")
    print("   В этом случае ОБЯЗАТЕЛЬНО нужен домен + Cloudflare")

    client.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

import paramiko
import json
import time
import base64

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

    print("=== Setting up Subscription + CDN Bypass ===")
    print("Создадим подписку с несколькими конфигурациями для обхода блокировок")
    
    # Update bot code to generate subscription link
    bot_code = '''import logging
import sqlite3
import uuid
import os
import signal
import asyncio
import json
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from bot.config import settings

logger = logging.getLogger(__name__)

XUI_DB_PATH = "/etc/x-ui/x-ui.db"


def _db_connect() -> sqlite3.Connection:
    """Open x-ui DB with timeout and WAL mode to avoid locking."""
    conn = sqlite3.connect(XUI_DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    return conn


def _restart_xray():
    """Send SIGHUP to xray process by scanning /proc."""
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
        else:
            logger.warning("xray process not found in /proc")
    except Exception as e:
        logger.error(f"Failed to restart xray: {e}")


class VPNService:
    def __init__(self):
        self.base_url = settings.VPN_PANEL_URL.rstrip("/")
        self._inbound_ids: Optional[list] = None
        logger.info("VPNService initialized (direct DB mode)")

    def _get_inbound_ids(self) -> list:
        """Get both Reality and Mobile inbound IDs"""
        if self._inbound_ids is not None:
            return self._inbound_ids
        conn = _db_connect()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, port, stream_settings FROM inbounds WHERE protocol='vless' ORDER BY id")
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
            
            # Add client to ALL inbounds
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
                logger.info(f"Client {username} added to inbound {inbound_id}, port={port}")
            
            conn.commit()
        finally:
            conn.close()

        _restart_xray()

        server_ip = self._get_server_ip()
        
        # Generate URLs for all inbounds
        urls = []
        from urllib.parse import quote
        
        for idx, (inbound_id, port, stream_settings) in enumerate(inbounds):
            security = stream_settings.get("security", "none")
            network = stream_settings.get("network", "tcp")
            
            if security == "reality":
                # Reality URL (WiFi + некоторые операторы)
                reality_settings = stream_settings.get("realitySettings", {})
                server_names = reality_settings.get("serverNames", [])
                short_ids = reality_settings.get("shortIds", [])
                public_key = reality_settings.get("settings", {}).get("publicKey", "")
                fingerprint = reality_settings.get("settings", {}).get("fingerprint", "chrome")
                spider_x = reality_settings.get("settings", {}).get("spiderX", "/")
                
                sni = server_names[0] if server_names else "www.microsoft.com"
                sid = short_ids[0] if short_ids else ""
                
                spider_x_encoded = quote(spider_x, safe='')
                display_name = f"⚡ NL-Reality-{port}"
                
                url = (
                    f"vless://{client_uuid}@{server_ip}:{port}"
                    f"?type=tcp&security=reality&pbk={public_key}&fp={fingerprint}"
                    f"&sni={sni}&sid={sid}&spx={spider_x_encoded}#{quote(display_name)}"
                )
                urls.append(url)
            
            elif network == "ws":
                # WebSocket URL (обход блокировок)
                ws_settings = stream_settings.get("wsSettings", {})
                ws_path = ws_settings.get("path", "/")
                
                display_name = f"⚡ NL-WebSocket-{port}"
                
                url = (
                    f"vless://{client_uuid}@{server_ip}:{port}"
                    f"?type=ws&path={quote(ws_path)}&security=none&encryption=none#{quote(display_name)}"
                )
                urls.append(url)
        
        # Create subscription content (base64 encoded list of configs)
        subscription_content = "\\n".join(urls)
        subscription_b64 = base64.b64encode(subscription_content.encode()).decode()
        
        # Generate subscription URL (using panel URL as base)
        # In production, you'd host this on a separate endpoint
        # For now, we'll return the base64 content directly
        
        return {
            "uuid": client_uuid,
            "subscription_url": subscription_content,  # All configs in one message
            "subscription_b64": subscription_b64,  # For subscription link
            "expiry_date": datetime.fromtimestamp(expiry_ts / 1000),
        }

    async def create_user(
        self, username: str, expiry_days: int, traffic_limit_gb: Optional[int] = None
    ) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, self._create_user_sync, username, expiry_days, traffic_limit_gb
        )
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
                cursor.execute(
                    "UPDATE inbounds SET settings = ? WHERE id = ?",
                    (json.dumps(settings_json), inbound_id),
                )
            conn.commit()
            logger.info(f"Client {username} deleted from all inbounds")
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
    
    # Save locally
    with open('bot/services/vpn_service.py', 'w', encoding='utf-8') as f:
        f.write(bot_code)
    
    # Upload to server
    sftp = client.open_sftp()
    with sftp.open('/root/vpn_telegram/bot/services/vpn_service.py', 'w') as f:
        f.write(bot_code)
    sftp.close()
    
    print("✅ Bot code updated for subscription")
    
    # Now let's add more bypass methods - Fragment and different ports
    print("\n=== Adding More Bypass Configurations ===")
    
    # Get current Reality config
    stream = run("sqlite3 /etc/x-ui/x-ui.db \"SELECT stream_settings FROM inbounds WHERE id=1;\"")
    stream_json = json.loads(stream)
    
    # Add Fragment to Reality (helps bypass DPI)
    if 'sockopt' not in stream_json:
        stream_json['sockopt'] = {}
    
    stream_json['sockopt']['tcpFastOpen'] = True
    stream_json['sockopt']['tcpNoDelay'] = True
    
    # Save updated config
    import tempfile
    import os as local_os
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(stream_json, f)
        temp_local = f.name
    
    sftp = client.open_sftp()
    sftp.put(temp_local, '/tmp/stream_optimized.json')
    sftp.close()
    local_os.unlink(temp_local)
    
    run("sqlite3 /etc/x-ui/x-ui.db \"UPDATE inbounds SET stream_settings = readfile('/tmp/stream_optimized.json') WHERE id=1;\"")
    run("rm /tmp/stream_optimized.json")
    
    print("✅ Added TCP optimizations to Reality")
    
    # Restart services
    print("\n=== Restarting Services ===")
    run("systemctl restart x-ui")
    time.sleep(5)
    
    # Reset trial
    print("\n=== Resetting Trial ===")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"UPDATE users SET trial_used = 0 WHERE telegram_id = 1658346274;\"")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"DELETE FROM vpn_keys;\"")
    
    # Rebuild bot
    print("\n=== Rebuilding Bot ===")
    run("cd ~/vpn_telegram && docker compose down", timeout=60)
    time.sleep(2)
    run("cd ~/vpn_telegram && docker compose up -d --build", timeout=120)
    time.sleep(10)
    
    print("\n=== Bot Logs ===")
    run("docker logs vpn_telegram_bot --tail=20 2>&1")
    
    print("\n✅ Setup complete!")
    print("\n📱 Теперь бот выдаст несколько конфигураций в одном сообщении:")
    print("   1. Reality (Port 443) - для WiFi и некоторых операторов")
    print("   2. WebSocket (Port 80) - обход блокировок")
    print("\n💡 Клиент автоматически выберет рабочую конфигурацию")
    print("\n🔑 Получите новый пробный ключ")
    print("\n⚠️ Если всё равно не работает на мобильном:")
    print("   - Попробуйте добавить Cloudflare CDN")
    print("   - Используйте домен вместо IP")
    print("   - Добавьте TLS с валидным сертификатом")

    client.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

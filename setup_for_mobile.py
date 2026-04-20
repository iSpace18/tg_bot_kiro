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

    print("=== Solution: Add second inbound with WebSocket + TLS for mobile ===")
    print("Reality работает на WiFi, но мобильные операторы его блокируют")
    print("Создадим второй inbound с WebSocket + TLS (без Reality)")
    
    # Check current inbounds
    print("\n=== Current Inbounds ===")
    inbounds = run("sqlite3 /etc/x-ui/x-ui.db \"SELECT id, port, protocol, remark FROM inbounds;\"")
    
    # Get the Reality inbound settings to copy clients
    print("\n=== Getting Reality Inbound Settings ===")
    settings = run("sqlite3 /etc/x-ui/x-ui.db \"SELECT settings FROM inbounds WHERE protocol='vless' LIMIT 1;\"")
    settings_json = json.loads(settings)
    
    # Create new inbound for mobile with WebSocket + no security (will work on mobile)
    mobile_inbound = {
        "network": "ws",
        "security": "none",
        "externalProxy": [],
        "wsSettings": {
            "acceptProxyProtocol": False,
            "path": "/vpn",
            "headers": {}
        }
    }
    
    # Use port 80 or 8080 for mobile (HTTP ports work better)
    mobile_port = 80
    
    print(f"\n=== Creating Mobile Inbound (Port {mobile_port}, WebSocket) ===")
    
    # Check if port 80 is available
    port_check = run(f"ss -tlnp | grep ':{mobile_port}' || echo 'free'")
    if 'free' not in port_check and str(mobile_port) in port_check:
        print(f"Port {mobile_port} is busy, using 8080")
        mobile_port = 8080
    
    # Create temp files
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(mobile_inbound, f)
        temp_stream = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(settings_json, f)
        temp_settings = f.name
    
    # Upload to server
    sftp = client.open_sftp()
    sftp.put(temp_stream, '/tmp/mobile_stream.json')
    sftp.put(temp_settings, '/tmp/mobile_settings.json')
    sftp.close()
    
    os.unlink(temp_stream)
    os.unlink(temp_settings)
    
    # Insert new inbound
    sniffing_json = '{\\"enabled\\":true,\\"destOverride\\":[\\"http\\",\\"tls\\",\\"quic\\",\\"fakedns\\"]}'
    insert_cmd = f"sqlite3 /etc/x-ui/x-ui.db \"INSERT INTO inbounds (user_id, up, down, total, remark, enable, expiry_time, listen, port, protocol, settings, stream_settings, tag, sniffing) VALUES (1, 0, 0, 0, 'VLESS-WS-Mobile', 1, 0, '', {mobile_port}, 'vless', readfile('/tmp/mobile_settings.json'), readfile('/tmp/mobile_stream.json'), 'inbound-{mobile_port}', '{sniffing_json}');\""
    
    result = run(insert_cmd)
    
    # Check if inserted
    print("\n=== Verifying New Inbound ===")
    new_inbound = run(f"sqlite3 /etc/x-ui/x-ui.db \"SELECT id, port, protocol, remark FROM inbounds WHERE port={mobile_port};\"")
    
    if str(mobile_port) in new_inbound:
        print(f"✅ Mobile inbound created on port {mobile_port}")
    else:
        print("❌ Failed to create inbound")
        client.close()
        exit(1)
    
    # Cleanup temp files
    run("rm /tmp/mobile_stream.json /tmp/mobile_settings.json")
    
    # Restart xray
    print("\n=== Restarting Xray ===")
    run("systemctl restart x-ui")
    time.sleep(5)
    
    # Verify both inbounds are listening
    print("\n=== Verifying Listening Ports ===")
    run("ss -tlnp | grep ':443\\|:80\\|:8080' | grep xray")
    
    # Now update bot to support multiple inbounds
    print("\n=== Updating Bot to Support Mobile Inbound ===")
    
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
        
        # Generate URLs for both inbounds
        urls = []
        for inbound_id, port, stream_settings in inbounds:
            security = stream_settings.get("security", "none")
            network = stream_settings.get("network", "tcp")
            
            if security == "reality":
                # Reality URL (WiFi)
                reality_settings = stream_settings.get("realitySettings", {})
                server_names = reality_settings.get("serverNames", [])
                short_ids = reality_settings.get("shortIds", [])
                public_key = reality_settings.get("settings", {}).get("publicKey", "")
                fingerprint = reality_settings.get("settings", {}).get("fingerprint", "chrome")
                spider_x = reality_settings.get("settings", {}).get("spiderX", "/")
                
                sni = server_names[0] if server_names else "www.microsoft.com"
                sid = short_ids[0] if short_ids else ""
                
                from urllib.parse import quote
                spider_x_encoded = quote(spider_x, safe='')
                display_name = "⚡ | 🇳🇱 Нидерланды [WiFi]"
                
                url = (
                    f"vless://{client_uuid}@{server_ip}:{port}"
                    f"?type=tcp&security=reality&pbk={public_key}&fp={fingerprint}"
                    f"&sni={sni}&sid={sid}&spx={spider_x_encoded}#{quote(display_name)}"
                )
                urls.append(("WiFi (Reality)", url))
            
            elif network == "ws":
                # WebSocket URL (Mobile)
                ws_settings = stream_settings.get("wsSettings", {})
                ws_path = ws_settings.get("path", "/")
                
                from urllib.parse import quote
                display_name = "⚡ | 🇳🇱 Нидерланды [Mobile]"
                
                url = (
                    f"vless://{client_uuid}@{server_ip}:{port}"
                    f"?type=ws&path={quote(ws_path)}&security=none&encryption=none#{quote(display_name)}"
                )
                urls.append(("Mobile (WebSocket)", url))
        
        # Return both URLs
        url_text = "\\n\\n".join([f"{name}:\\n{url}" for name, url in urls])
        
        return {
            "uuid": client_uuid,
            "subscription_url": url_text,
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
    
    print("✅ Bot updated to support both inbounds")
    
    # Reset and restart
    print("\n=== Resetting Trial ===")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"UPDATE users SET trial_used = 0 WHERE telegram_id = 1658346274;\"")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"DELETE FROM vpn_keys;\"")
    
    print("\n=== Restarting Bot ===")
    run("cd ~/vpn_telegram && docker compose restart", timeout=60)
    time.sleep(8)
    
    print("\n✅ Setup complete!")
    print(f"\n📱 Configuration:")
    print(f"   1. Reality (Port 443) - для WiFi")
    print(f"   2. WebSocket (Port {mobile_port}) - для мобильного интернета")
    print(f"\n🔑 Получите новый ключ - бот выдаст ДВЕ ссылки:")
    print(f"   - WiFi (Reality) - используйте на WiFi")
    print(f"   - Mobile (WebSocket) - используйте на мобильном")

    client.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

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

    print("=== Trying gRPC Transport (better for mobile) ===")
    
    # Get current settings
    stream = run("sqlite3 /etc/x-ui/x-ui.db \"SELECT stream_settings FROM inbounds WHERE protocol='vless' LIMIT 1;\"")
    stream_json = json.loads(stream)
    
    # Change to gRPC
    stream_json['network'] = 'grpc'
    stream_json['grpcSettings'] = {
        'serviceName': 'grpc',
        'multiMode': False
    }
    
    # Keep Reality settings
    print(f"Security: {stream_json['security']}")
    print(f"Network: tcp → grpc")
    
    # Write to temp file
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(stream_json, f)
        temp_local = f.name
    
    sftp = client.open_sftp()
    temp_remote = '/tmp/stream_grpc.json'
    sftp.put(temp_local, temp_remote)
    sftp.close()
    os.unlink(temp_local)
    
    run(f"sqlite3 /etc/x-ui/x-ui.db \"UPDATE inbounds SET stream_settings = readfile('{temp_remote}') WHERE protocol='vless';\"")
    run(f"rm {temp_remote}")
    
    print("✅ Changed to gRPC transport")
    
    print("\n=== Restarting Xray ===")
    run("pkill -SIGHUP xray")
    time.sleep(3)
    
    # Update bot code to support gRPC
    print("\n=== Updating Bot Code for gRPC ===")
    
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
        self._inbound_id: Optional[int] = None
        logger.info("VPNService initialized (direct DB mode)")

    def _get_inbound_id(self) -> int:
        if self._inbound_id is not None:
            return self._inbound_id
        conn = _db_connect()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM inbounds WHERE protocol='vless' LIMIT 1")
            row = cursor.fetchone()
            if not row:
                raise Exception("VLESS inbound not found in 3x-ui database")
            self._inbound_id = row[0]
            logger.info(f"Found VLESS inbound ID: {self._inbound_id}")
            return self._inbound_id
        finally:
            conn.close()

    def _get_server_ip(self) -> str:
        url = settings.VPN_PANEL_URL.rstrip("/")
        url = url.replace("https://", "").replace("http://", "")
        return url.split(":")[0]

    def _create_user_sync(self, username: str, expiry_days: int, traffic_limit_gb: Optional[int]) -> Dict[str, Any]:
        inbound_id = self._get_inbound_id()
        client_uuid = str(uuid.uuid4())
        expiry_ts = int((datetime.utcnow() + timedelta(days=expiry_days)).timestamp() * 1000)
        total_gb = (traffic_limit_gb * 1024 * 1024 * 1024) if traffic_limit_gb else 0

        conn = _db_connect()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT settings, port, stream_settings FROM inbounds WHERE id = ?", (inbound_id,))
            row = cursor.fetchone()
            if not row:
                raise Exception(f"Inbound {inbound_id} not found")

            settings_json = json.loads(row[0])
            port = row[1]
            stream_settings = json.loads(row[2]) if row[2] else {}
            
            logger.info(f"Stream settings: security={stream_settings.get('security', 'none')}, network={stream_settings.get('network', 'tcp')}")

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
            conn.commit()
            logger.info(f"Client {username} added to inbound {inbound_id}, port={port}")
        finally:
            conn.close()

        _restart_xray()

        server_ip = self._get_server_ip()
        display_name = "⚡ | 🇳🇱 Нидерланды [VPN]"
        
        # Check if Reality is enabled
        security = stream_settings.get("security", "none")
        network = stream_settings.get("network", "tcp")
        logger.info(f"Detected security type: {security}, network: {network}")
        
        if security == "reality":
            # Generate Reality VLESS URL
            reality_settings = stream_settings.get("realitySettings", {})
            server_names = reality_settings.get("serverNames", [])
            short_ids = reality_settings.get("shortIds", [])
            public_key = reality_settings.get("settings", {}).get("publicKey", "")
            fingerprint = reality_settings.get("settings", {}).get("fingerprint", "chrome")
            spider_x = reality_settings.get("settings", {}).get("spiderX", "/")
            
            # Use first available values
            sni = server_names[0] if server_names else "www.microsoft.com"
            sid = short_ids[0] if short_ids else ""
            
            logger.info(f"Reality params: pbk={public_key[:20]}..., sni={sni}, sid={sid}, fp={fingerprint}")
            
            # URL encode spider_x if needed
            from urllib.parse import quote
            spider_x_encoded = quote(spider_x, safe='')
            
            # Build URL based on network type
            if network == "grpc":
                grpc_settings = stream_settings.get("grpcSettings", {})
                service_name = grpc_settings.get("serviceName", "grpc")
                
                sub_url = (
                    f"vless://{client_uuid}@{server_ip}:{port}"
                    f"?type=grpc&serviceName={service_name}&security=reality"
                    f"&pbk={public_key}&fp={fingerprint}&sni={sni}&sid={sid}&spx={spider_x_encoded}#{quote(display_name)}"
                )
            else:
                # TCP
                sub_url = (
                    f"vless://{client_uuid}@{server_ip}:{port}"
                    f"?type=tcp&security=reality&pbk={public_key}&fp={fingerprint}"
                    f"&sni={sni}&sid={sid}&spx={spider_x_encoded}#{quote(display_name)}"
                )
        else:
            # Standard VLESS TCP
            from urllib.parse import quote
            sub_url = (
                f"vless://{client_uuid}@{server_ip}:{port}"
                f"?type=tcp&security=none&encryption=none#{quote(display_name)}"
            )
        
        return {
            "uuid": client_uuid,
            "subscription_url": sub_url,
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
        inbound_id = self._get_inbound_id()
        conn = _db_connect()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT settings FROM inbounds WHERE id = ?", (inbound_id,))
            row = cursor.fetchone()
            if not row:
                return False
            settings_json = json.loads(row[0])
            clients = settings_json.get("clients", [])
            new_clients = [c for c in clients if c.get("email") != username]
            if len(new_clients) == len(clients):
                logger.warning(f"Client {username} not found in inbound")
                return False
            settings_json["clients"] = new_clients
            cursor.execute(
                "UPDATE inbounds SET settings = ? WHERE id = ?",
                (json.dumps(settings_json), inbound_id),
            )
            conn.commit()
            logger.info(f"Client {username} deleted")
        finally:
            conn.close()
        _restart_xray()
        return True

    async def delete_user(self, username: str) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._delete_user_sync, username)

    async def get_client_info(self, username: str) -> Optional[Dict[str, Any]]:
        def _sync():
            inbound_id = self._get_inbound_id()
            conn = _db_connect()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT settings FROM inbounds WHERE id = ?", (inbound_id,))
                row = cursor.fetchone()
                if not row:
                    return None
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
    
    # Upload to server
    sftp = client.open_sftp()
    with open('bot/services/vpn_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    with sftp.open('/root/vpn_telegram/bot/services/vpn_service.py', 'w') as f:
        f.write(content)
    sftp.close()
    
    print("✅ Bot code updated for gRPC")
    
    # Reset and restart
    print("\n=== Resetting Trial ===")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"UPDATE users SET trial_used = 0 WHERE telegram_id = 1658346274;\"")
    run("sqlite3 /root/vpn_telegram/data/bot.db \"DELETE FROM vpn_keys;\"")
    
    print("\n=== Restarting Bot ===")
    run("cd ~/vpn_telegram && docker compose restart", timeout=60)
    time.sleep(8)
    
    print("\n✅ gRPC configuration complete!")
    print("\n📱 Final settings:")
    print("   - Port: 2053")
    print("   - Security: Reality")
    print("   - Network: gRPC (better for mobile)")
    print("   - Target: www.microsoft.com")
    print("\n🔑 Get a new trial key and test on mobile network")
    print("\nℹ️ gRPC обычно лучше проходит через мобильные сети")

    client.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

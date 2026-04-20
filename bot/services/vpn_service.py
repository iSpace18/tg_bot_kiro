import logging
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
                    cmdline = f.read().replace(b'\x00', b' ').decode(errors='ignore')
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
        self.mock_mode = settings.VPN_MOCK_MODE
        if self.mock_mode:
            logger.warning("VPNService running in MOCK MODE (for testing only)")
        else:
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
        # Mock mode for testing
        if self.mock_mode:
            client_uuid = str(uuid.uuid4())
            expiry_date = datetime.utcnow() + timedelta(days=expiry_days)
            server_ip = "mock.vpn.server"
            port = 443
            display_name = "⚡ | 🇳🇱 Нидерланды [VPN] [MOCK]"
            sub_url = (
                f"vless://{client_uuid}@{server_ip}:{port}"
                f"?type=tcp&security=none&encryption=none#{display_name}"
            )
            logger.info(f"MOCK: Created user {username} with UUID {client_uuid}")
            return {
                "uuid": client_uuid,
                "subscription_url": sub_url,
                "expiry_date": expiry_date,
            }
        
        # Real mode - direct DB access
        inbound_id = self._get_inbound_id()
        client_uuid = str(uuid.uuid4())
        expiry_ts = int((datetime.utcnow() + timedelta(days=expiry_days)).timestamp() * 1000)
        total_gb = (traffic_limit_gb * 1024 * 1024 * 1024) if traffic_limit_gb else 0

        conn = _db_connect()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT settings, port FROM inbounds WHERE id = ?", (inbound_id,))
            row = cursor.fetchone()
            if not row:
                raise Exception(f"Inbound {inbound_id} not found")

            settings_json = json.loads(row[0])
            port = row[1]

            new_client = {
                "id": client_uuid,
                "email": username,
                "flow": "xtls-rprx-vision",
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
        
        # Beautiful name for VPN apps with flag and description
        display_name = "⚡ VLESS-Reality | Netherlands 🇳🇱"
        
        # Reality-optimized URL with proper parameters
        from urllib.parse import quote
        sub_url = (
            f"vless://{client_uuid}@{server_ip}:{port}"
            f"?type=tcp&security=reality&pbk=c4d33NKVpulPMhdJOcq-e12fjJjRZMU5V_wTTIm5K2c"
            f"&fp=chrome&sni=www.google.com&sid=0123456789abcdef&spx=%2F"
            f"&flow=xtls-rprx-vision"
            f"#{quote(display_name)}"
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
        # Mock mode for testing
        if self.mock_mode:
            logger.info(f"MOCK: Deleted user {username}")
            return True
        
        # Real mode - direct DB access
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
            # Mock mode for testing
            if self.mock_mode:
                logger.info(f"MOCK: Getting client info for {username}")
                return {
                    "email": username,
                    "enable": True,
                    "expiryTime": int((datetime.utcnow() + timedelta(days=30)).timestamp() * 1000),
                }
            
            # Real mode - direct DB access
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

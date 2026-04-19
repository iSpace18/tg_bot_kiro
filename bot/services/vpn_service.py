import logging
import sqlite3
import uuid
import os
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

            # Read current settings
            cursor.execute("SELECT settings, port FROM inbounds WHERE id = ?", (inbound_id,))
            row = cursor.fetchone()
            if not row:
                raise Exception(f"Inbound {inbound_id} not found")

            settings_json = json.loads(row[0])
            port = row[1]

            # Add new client (no 'flow' field)
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

            # Write back
            cursor.execute(
                "UPDATE inbounds SET settings = ? WHERE id = ?",
                (json.dumps(settings_json), inbound_id),
            )
            conn.commit()
            logger.info(f"Client {username} added to inbound {inbound_id}, port={port}")
        finally:
            conn.close()

        # Restart xray
        os.system("x-ui restart >/dev/null 2>&1 &")

        server_ip = self._get_server_ip()
        sub_url = (
            f"vless://{client_uuid}@{server_ip}:{port}"
            f"?type=tcp&security=none&encryption=none#{username}"
        )
        return {
            "uuid": client_uuid,
            "subscription_url": sub_url,
            "expiry_date": datetime.fromtimestamp(expiry_ts / 1000),
        }

    async def create_user(
        self, username: str, expiry_days: int, traffic_limit_gb: Optional[int] = None
    ) -> Dict[str, Any]:
        # Run blocking DB operation in thread pool to not block event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, self._create_user_sync, username, expiry_days, traffic_limit_gb
        )
        # Wait for xray to restart (non-blocking)
        await asyncio.sleep(4)
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

        os.system("x-ui restart >/dev/null 2>&1 &")
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
                for client in data.get("clients", []):
                    if client.get("email") == username:
                        return client
                return None
            finally:
                conn.close()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync)


vpn_service = VPNService()

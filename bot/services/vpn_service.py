import logging
import sqlite3
import uuid
import os
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from bot.config import settings

logger = logging.getLogger(__name__)

XUI_DB_PATH = "/etc/x-ui/x-ui.db"


class VPNService:
    def __init__(self):
        self.base_url = settings.VPN_PANEL_URL.rstrip("/")
        self.inbound_id = self._get_inbound_id_from_db()
        logger.info(f"Using 3x-ui direct DB mode. Inbound ID: {self.inbound_id}")

    def _get_inbound_id_from_db(self) -> int:
        conn = sqlite3.connect(XUI_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM inbounds WHERE protocol='vless' LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        if not row:
            raise Exception("VLESS inbound not found in 3x-ui database")
        return row[0]

    def _get_server_ip(self) -> str:
        # Extract IP from VPN_PANEL_URL
        url = settings.VPN_PANEL_URL.rstrip("/")
        # Remove protocol
        url = url.replace("https://", "").replace("http://", "")
        # Remove port
        ip = url.split(":")[0]
        return ip

    async def create_user(
        self, username: str, expiry_days: int, traffic_limit_gb: Optional[int] = None
    ) -> Dict[str, Any]:
        client_uuid = str(uuid.uuid4())
        expiry_timestamp = int(
            (datetime.utcnow() + timedelta(days=expiry_days)).timestamp() * 1000
        )
        total_gb = (traffic_limit_gb * 1024 * 1024 * 1024) if traffic_limit_gb else 0

        conn = sqlite3.connect(XUI_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE inbounds
            SET settings = json_insert(
                settings,
                '$.clients[#]',
                json_object(
                    'id', ?,
                    'email', ?,
                    'enable', 1,
                    'expiryTime', ?,
                    'totalGB', ?,
                    'limitIp', 1
                )
            )
            WHERE id = ?
            """,
            (client_uuid, username, expiry_timestamp, total_gb, self.inbound_id),
        )
        conn.commit()
        conn.close()

        os.system("x-ui restart >/dev/null 2>&1 &")
        time.sleep(4)

        conn = sqlite3.connect(XUI_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT port FROM inbounds WHERE id = ?", (self.inbound_id,))
        port = cursor.fetchone()[0]
        conn.close()

        server_ip = self._get_server_ip()
        sub_url = (
            f"vless://{client_uuid}@{server_ip}:{port}"
            f"?type=tcp&security=none&encryption=none#{username}"
        )
        logger.info(f"Client created: {username}, uuid={client_uuid}")
        return {
            "uuid": client_uuid,
            "subscription_url": sub_url,
            "expiry_date": datetime.fromtimestamp(expiry_timestamp / 1000),
        }

    async def delete_user(self, username: str) -> bool:
        try:
            conn = sqlite3.connect(XUI_DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE inbounds
                SET settings = json_remove(
                    settings,
                    (SELECT fullkey FROM json_each(settings, '$.clients')
                     WHERE json_extract(value, '$.email') = ?)
                )
                WHERE id = ?
                """,
                (username, self.inbound_id),
            )
            conn.commit()
            conn.close()
            os.system("x-ui restart >/dev/null 2>&1 &")
            logger.info(f"Client deleted: {username}")
            return True
        except Exception as e:
            logger.error(f"Error deleting user {username}: {e}")
            return False

    async def get_client_info(self, username: str) -> Optional[Dict[str, Any]]:
        try:
            conn = sqlite3.connect(XUI_DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT settings FROM inbounds WHERE id = ?", (self.inbound_id,)
            )
            row = cursor.fetchone()
            conn.close()
            if not row:
                return None
            import json
            data = json.loads(row[0])
            for client in data.get("clients", []):
                if client.get("email") == username:
                    return client
            return None
        except Exception as e:
            logger.error(f"Error getting client info: {e}")
            return None


vpn_service = VPNService()

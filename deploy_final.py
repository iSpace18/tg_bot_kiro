import paramiko, time

HOST, USER, PASS = "89.44.76.190", "root", "Mb69Bs5T18hNvrw5FC"
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=15)

def run(cmd, timeout=120):
    print(f"$ {cmd}")
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out: print(out)
    if err: print("ERR:", err)
    return out

sftp = client.open_sftp()

# Write updated docker-compose.yml
dc = """version: '3.8'

services:
  bot:
    build: .
    container_name: vpn_telegram_bot
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - /etc/x-ui:/etc/x-ui:rw
      - /usr/local/bin/restart-xui.sh:/usr/local/bin/restart-xui.sh:ro
      - /var/run/dbus:/var/run/dbus
      - /run/systemd:/run/systemd
    network_mode: host
    privileged: true
"""
with sftp.open('/root/vpn_telegram/docker-compose.yml', 'w') as f:
    f.write(dc)
print("Written docker-compose.yml")

# Write updated vpn_service.py
vpn = '''import logging
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
RESTART_SCRIPT = "/usr/local/bin/restart-xui.sh"


def _db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(XUI_DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    return conn


def _restart_xray():
    """Restart x-ui/xray via host systemctl through mounted script."""
    ret = os.system(f"{RESTART_SCRIPT} >/dev/null 2>&1")
    logger.info(f"Xray restart exit code: {ret}")


class VPNService:
    def __init__(self):
        self.base_url = settings.VPN_PANEL_URL.rstrip("/")
        self._inbound_id = None
        logger.info("VPNService initialized (direct DB mode)")

    def _get_inbound_id(self) -> int:
        if self._inbound_id is not None:
            return self._inbound_id
        conn = _db_connect()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM inbounds WHERE protocol=\'vless\' LIMIT 1")
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

    def _create_user_sync(self, username: str, expiry_days: int, traffic_limit_gb) -> Dict[str, Any]:
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
        sub_url = (
            f"vless://{client_uuid}@{server_ip}:{port}"
            f"?type=tcp&security=none&encryption=none#{username}"
        )
        return {
            "uuid": client_uuid,
            "subscription_url": sub_url,
            "expiry_date": datetime.fromtimestamp(expiry_ts / 1000),
        }

    async def create_user(self, username: str, expiry_days: int, traffic_limit_gb=None) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._create_user_sync, username, expiry_days, traffic_limit_gb)
        await asyncio.sleep(5)
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
                return False
            settings_json["clients"] = new_clients
            cursor.execute(
                "UPDATE inbounds SET settings = ? WHERE id = ?",
                (json.dumps(settings_json), inbound_id),
            )
            conn.commit()
        finally:
            conn.close()
        _restart_xray()
        return True

    async def delete_user(self, username: str) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._delete_user_sync, username)

    async def get_client_info(self, username: str):
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

with sftp.open('/root/vpn_telegram/bot/services/vpn_service.py', 'w') as f:
    f.write(vpn)
print("Written vpn_service.py")
sftp.close()

# Rebuild and restart
run("cd ~/vpn_telegram && docker compose down")
run("cd ~/vpn_telegram && docker compose build --no-cache 2>&1 | tail -5", timeout=300)
run("cd ~/vpn_telegram && docker compose up -d")
time.sleep(8)
run("cd ~/vpn_telegram && docker compose logs --tail=20 2>&1")
run("cd ~/vpn_telegram && docker compose ps 2>&1")

# Test restart script works from inside container
print("\n=== Testing restart script from container ===")
run("docker exec vpn_telegram_bot ls -la /usr/local/bin/restart-xui.sh")
run("docker exec vpn_telegram_bot /usr/local/bin/restart-xui.sh && echo 'RESTART OK'")
time.sleep(5)
run("ss -tlnp | grep 29545")

client.close()
print("Done!")

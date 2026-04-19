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

# Update restart script to use kill -HUP (works from container since network_mode: host shares PID namespace... wait, no)
# Actually with network_mode: host we still have separate PID namespace
# But with privileged: true we can access /proc of host
# Let's use: kill -HUP $(cat /proc/*/cmdline 2>/dev/null | grep -la xray | ...)
# Simpler: use nsenter into PID namespace

# Actually the cleanest: write xray PID to a file, container reads it and sends HUP
# OR: use x-ui API from container (localhost:2053 is accessible via network_mode: host)

vpn_service = '''import logging
import sqlite3
import uuid
import os
import signal
import asyncio
import json
import subprocess
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
    """Send SIGHUP to xray process to reload config."""
    try:
        # Find xray PID via /proc (accessible in privileged container)
        result = subprocess.run(
            ["pgrep", "-f", "xray-linux"],
            capture_output=True, text=True
        )
        pids = result.stdout.strip().split()
        if pids:
            for pid in pids:
                os.kill(int(pid), signal.SIGHUP)
            logger.info(f"Sent SIGHUP to xray PIDs: {pids}")
        else:
            logger.warning("xray process not found, trying x-ui restart")
            os.system("x-ui restart >/dev/null 2>&1 &")
    except Exception as e:
        logger.error(f"Failed to restart xray: {e}")
        os.system("x-ui restart >/dev/null 2>&1 &")


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
    f.write(vpn_service)
print("Written vpn_service.py")

# Simplify docker-compose - no need for systemctl mount
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
    network_mode: host
    privileged: true
"""
with sftp.open('/root/vpn_telegram/docker-compose.yml', 'w') as f:
    f.write(dc)
print("Written docker-compose.yml")
sftp.close()

# Rebuild
run("cd ~/vpn_telegram && docker compose down")
run("cd ~/vpn_telegram && docker compose up -d --build 2>&1 | tail -5", timeout=300)
time.sleep(8)

# Test: check if pgrep works inside container
print("=== Test pgrep from container ===")
run("docker exec vpn_telegram_bot pgrep -f xray-linux")

# Test full flow: add a test client and check xray reloads
print("=== Test SIGHUP from container ===")
run("""docker exec vpn_telegram_bot python3 -c "
import subprocess, os, signal
r = subprocess.run(['pgrep', '-f', 'xray-linux'], capture_output=True, text=True)
pids = r.stdout.strip().split()
print('xray PIDs:', pids)
for pid in pids:
    os.kill(int(pid), signal.SIGHUP)
    print(f'Sent SIGHUP to {pid}')
" """)

time.sleep(3)
run("ss -tlnp | grep 29545")
run("cd ~/vpn_telegram && docker compose logs --tail=15 2>&1")

client.close()
print("Done!")

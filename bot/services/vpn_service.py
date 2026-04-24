import logging
import sqlite3
import uuid
import os
import signal
import asyncio
import json
import aiohttp
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
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_cookie: Optional[str] = None
        if self.mock_mode:
            logger.warning("VPNService running in MOCK MODE (for testing only)")
        else:
            logger.info("VPNService initialized (direct DB mode)")

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Create or reuse aiohttp session with proper timeout."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            # Disable SSL verification for self-signed certificates
            connector = aiohttp.TCPConnector(ssl=False)
            self._session = aiohttp.ClientSession(timeout=timeout, connector=connector)
            logger.debug("Created new aiohttp session with SSL verification disabled")
        return self._session

    async def _login(self) -> None:
        """
        Authenticate with x-ui panel and obtain session cookie.
        
        POSTs to /login with form-encoded credentials, extracts session cookie
        from response headers, and stores it for subsequent API calls.
        
        Implements retry logic with exponential backoff for transient network errors.
        
        Raises:
            Exception: If authentication fails after all retries
        """
        session = await self._ensure_session()
        login_url = f"{self.base_url}/login"
        
        # Form-encoded credentials
        form_data = aiohttp.FormData()
        form_data.add_field('username', settings.VPN_PANEL_USERNAME)
        form_data.add_field('password', settings.VPN_PANEL_PASSWORD)
        
        # Retry logic with exponential backoff
        max_retries = 3
        base_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Attempting x-ui login (attempt {attempt + 1}/{max_retries})")
                
                async with session.post(login_url, data=form_data) as response:
                    # Check for authentication failure
                    if response.status == 401:
                        error_msg = "Authentication failed: Invalid username or password"
                        logger.error(error_msg)
                        raise Exception(error_msg)
                    
                    if response.status == 403:
                        error_msg = "Authentication failed: Access forbidden"
                        logger.error(error_msg)
                        raise Exception(error_msg)
                    
                    if response.status != 200:
                        error_msg = f"Authentication failed: HTTP {response.status}"
                        logger.error(error_msg)
                        raise Exception(error_msg)
                    
                    # Extract session cookie from response headers
                    cookies = response.cookies
                    if 'session' in cookies:
                        self._session_cookie = cookies['session'].value
                        logger.info("Successfully authenticated with x-ui panel")
                        logger.debug(f"Session cookie obtained: {self._session_cookie[:20]}...")
                        return
                    
                    # Check for 3x-ui cookie (x-ui uses this name)
                    if '3x-ui' in cookies:
                        self._session_cookie = cookies['3x-ui'].value
                        logger.info("Successfully authenticated with x-ui panel")
                        logger.debug(f"Session cookie obtained: {self._session_cookie[:20]}...")
                        return
                    
                    # Check Set-Cookie header as fallback
                    set_cookie = response.headers.get('Set-Cookie', '')
                    if 'session=' in set_cookie:
                        # Extract session value from Set-Cookie header
                        cookie_parts = set_cookie.split(';')
                        for part in cookie_parts:
                            if 'session=' in part:
                                self._session_cookie = part.split('=', 1)[1]
                                logger.info("Successfully authenticated with x-ui panel")
                                logger.debug(f"Session cookie obtained from Set-Cookie: {self._session_cookie[:20]}...")
                                return
                    
                    # Check for 3x-ui in Set-Cookie header
                    if '3x-ui=' in set_cookie:
                        cookie_parts = set_cookie.split(';')
                        for part in cookie_parts:
                            if '3x-ui=' in part:
                                self._session_cookie = part.split('=', 1)[1]
                                logger.info("Successfully authenticated with x-ui panel")
                                logger.debug(f"Session cookie obtained from Set-Cookie: {self._session_cookie[:20]}...")
                                return
                    
                    error_msg = "Authentication failed: No session cookie in response"
                    logger.error(error_msg)
                    raise Exception(error_msg)
            
            except aiohttp.ClientError as e:
                # Transient network errors - retry with exponential backoff
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(f"Network error during login (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    error_msg = f"Authentication failed after {max_retries} retries: {e}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
            
            except Exception as e:
                # Non-retryable errors (auth failures, missing cookies)
                error_msg = f"Authentication failed: {e}"
                logger.error(error_msg)
                raise Exception(error_msg)

    async def close(self):
        """Properly close aiohttp session on shutdown."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("Closed aiohttp session")
            self._session = None
            self._session_cookie = None

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

    def _create_user_direct_db(self, username: str, expiry_days: int, traffic_limit_gb: Optional[int]) -> Dict[str, Any]:
        """
        Fallback method: Create user via direct database access.
        
        This method bypasses x-ui API and directly modifies the SQLite database.
        WARNING: This prevents x-ui from initializing statistics tracking.
        Only used as fallback when API is unavailable.
        """
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

        # Generate CDN bypass configuration (works during RKN blocks via Cloudflare)
        from urllib.parse import quote
        
        # CDN bypass connection via djanvpn.ru domain with matching SNI
        config_name = "Netherlands VPN"
        subscription_url = (
            f"vless://{client_uuid}@djanvpn.ru:{port}"
            f"?type=tcp&security=reality&pbk=c4d33NKVpulPMhdJOcq-e12fjJjRZMU5V_wTTIm5K2c"
            f"&fp=chrome&sni=djanvpn.ru&sid=0123456789abcdef&spx=%2F"
            f"&flow=xtls-rprx-vision"
            f"#{quote(config_name)}"
        )
        
        return {
            "uuid": client_uuid,
            "subscription_url": subscription_url,
            "expiry_date": datetime.fromtimestamp(expiry_ts / 1000),
        }

    async def _create_user_api(self, username: str, expiry_days: int, traffic_limit_gb: Optional[int]) -> Dict[str, Any]:
        """
        Create user via x-ui API (preferred method).
        
        This method uses x-ui's official API to create clients, ensuring proper
        statistics tracking initialization. Falls back to direct DB access if API fails.
        
        Args:
            username: Client email/username
            expiry_days: Number of days until expiration
            traffic_limit_gb: Traffic limit in GB (None for unlimited)
            
        Returns:
            Dict with uuid, subscription_url, and expiry_date
        """
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
        
        try:
            # Authenticate with x-ui panel
            await self._login()
            
            # Get inbound ID and port
            inbound_id = self._get_inbound_id()
            
            # Generate client UUID and calculate expiry timestamp
            client_uuid = str(uuid.uuid4())
            expiry_ts = int((datetime.utcnow() + timedelta(days=expiry_days)).timestamp() * 1000)
            total_gb = (traffic_limit_gb * 1024 * 1024 * 1024) if traffic_limit_gb else 0
            
            # Get port from database for subscription URL
            conn = _db_connect()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT port FROM inbounds WHERE id = ?", (inbound_id,))
                row = cursor.fetchone()
                if not row:
                    raise Exception(f"Inbound {inbound_id} not found")
                port = row[0]
            finally:
                conn.close()
            
            # Prepare API request payload
            client_data = {
                "id": client_uuid,
                "email": username,
                "flow": "xtls-rprx-vision",
                "enable": True,
                "expiryTime": expiry_ts,
                "totalGB": total_gb,
                "limitIp": 1,
            }
            
            payload = {
                "id": inbound_id,
                "settings": json.dumps({"clients": [client_data]})
            }
            
            # Make API request
            session = await self._ensure_session()
            api_url = f"{self.base_url}/panel/api/inbounds/addClient"
            headers = {"Cookie": f"3x-ui={self._session_cookie}"}
            
            logger.debug(f"API Request: POST {api_url}")
            logger.debug(f"Payload: {payload}")
            
            async with session.post(api_url, json=payload, headers=headers) as response:
                response_text = await response.text()
                logger.debug(f"API Response: {response.status} - {response_text}")
                
                if response.status != 200:
                    raise Exception(f"API returned status {response.status}: {response_text}")
                
                try:
                    response_data = json.loads(response_text)
                    if not response_data.get("success"):
                        raise Exception(f"API returned success=false: {response_text}")
                except json.JSONDecodeError:
                    raise Exception(f"Invalid JSON response: {response_text}")
            
            logger.info(f"Client {username} created via API (inbound {inbound_id}, UUID {client_uuid})")
            
            # Generate CDN bypass configuration (works during RKN blocks via Cloudflare)
            from urllib.parse import quote
            
            # CDN bypass connection via djanvpn.ru domain with matching SNI
            config_name = "Netherlands VPN"
            subscription_url = (
                f"vless://{client_uuid}@djanvpn.ru:{port}"
                f"?type=tcp&security=reality&pbk=c4d33NKVpulPMhdJOcq-e12fjJjRZMU5V_wTTIm5K2c"
                f"&fp=chrome&sni=djanvpn.ru&sid=0123456789abcdef&spx=%2F"
                f"&flow=xtls-rprx-vision"
                f"#{quote(config_name)}"
            )
            
            return {
                "uuid": client_uuid,
                "subscription_url": subscription_url,
                "expiry_date": datetime.fromtimestamp(expiry_ts / 1000),
            }
            
        except Exception as e:
            logger.warning(f"API client creation failed: {e}. Falling back to direct DB access.")
            # Fallback to direct database access
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._create_user_direct_db, username, expiry_days, traffic_limit_gb
            )

    async def create_user(
        self, username: str, expiry_days: int, traffic_limit_gb: Optional[int] = None
    ) -> Dict[str, Any]:
        # Mock mode check preserved at beginning
        if self.mock_mode:
            return await self._create_user_api(username, expiry_days, traffic_limit_gb)
        
        # Use API-based creation (with fallback to direct DB)
        result = await self._create_user_api(username, expiry_days, traffic_limit_gb)
        await asyncio.sleep(3)
        return result

    def _delete_user_direct_db(self, username: str) -> bool:
        """
        Fallback method: Delete user via direct database access.
        
        This method bypasses x-ui API and directly modifies the SQLite database.
        WARNING: This may leave stale entries in client_traffics table.
        Only used as fallback when API is unavailable.
        """
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

    async def _delete_user_api(self, username: str) -> bool:
        """
        Delete user via x-ui API (preferred method).
        
        This method uses x-ui's official API to delete clients, ensuring proper
        cleanup of statistics tracking entries. Falls back to direct DB access if API fails.
        
        Args:
            username: Client email/username to delete
            
        Returns:
            Boolean indicating success
        """
        # Mock mode for testing
        if self.mock_mode:
            logger.info(f"MOCK: Deleted user {username}")
            return True
        
        try:
            # Authenticate with x-ui panel
            await self._login()
            
            # Get inbound ID
            inbound_id = self._get_inbound_id()
            
            # Prepare API request payload
            payload = {
                "id": inbound_id,
                "email": username
            }
            
            # Make API request
            session = await self._ensure_session()
            api_url = f"{self.base_url}/panel/api/inbounds/delClient"
            headers = {"Cookie": f"3x-ui={self._session_cookie}"}
            
            logger.debug(f"API Request: POST {api_url}")
            logger.debug(f"Payload: {payload}")
            
            async with session.post(api_url, json=payload, headers=headers) as response:
                response_text = await response.text()
                logger.debug(f"API Response: {response.status} - {response_text}")
                
                if response.status != 200:
                    raise Exception(f"API returned status {response.status}: {response_text}")
                
                try:
                    response_data = json.loads(response_text)
                    if not response_data.get("success"):
                        raise Exception(f"API returned success=false: {response_text}")
                except json.JSONDecodeError:
                    raise Exception(f"Invalid JSON response: {response_text}")
            
            logger.info(f"Client {username} deleted via API (inbound {inbound_id})")
            return True
            
        except Exception as e:
            logger.warning(f"API client deletion failed: {e}. Falling back to direct DB access.")
            # Fallback to direct database access
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._delete_user_direct_db, username)

    async def delete_user(self, username: str) -> bool:
        # Mock mode check preserved at beginning
        if self.mock_mode:
            return await self._delete_user_api(username)
        
        # Use API-based deletion (with fallback to direct DB)
        return await self._delete_user_api(username)

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

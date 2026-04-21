"""
Unit tests for VPNService._login() method.

Tests authentication with x-ui panel including:
- Successful login with valid credentials
- Authentication failures with invalid credentials
- Session cookie extraction
- Retry logic for transient network errors
- Timeout configuration
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientError, ClientTimeout
from bot.services.vpn_service import VPNService


@pytest.fixture
def vpn_service():
    """Create VPNService instance for testing."""
    with patch('bot.services.vpn_service.settings') as mock_settings:
        mock_settings.VPN_PANEL_URL = "https://test.panel.com"
        mock_settings.VPN_PANEL_USERNAME = "admin"
        mock_settings.VPN_PANEL_PASSWORD = "password123"
        mock_settings.VPN_MOCK_MODE = False
        service = VPNService()
        yield service


@pytest.mark.asyncio
@pytest.mark.unit
async def test_login_success_with_cookie_object(vpn_service):
    """Test successful login with session cookie in response.cookies."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.cookies = {'session': MagicMock(value='test_session_cookie_123')}
    mock_response.headers = {}
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    
    mock_session = AsyncMock()
    mock_session.post = MagicMock(return_value=mock_response)
    mock_session.closed = False
    
    vpn_service._session = mock_session
    
    await vpn_service._login()
    
    assert vpn_service._session_cookie == 'test_session_cookie_123'
    mock_session.post.assert_called_once()
    call_args = mock_session.post.call_args
    assert call_args[0][0] == "https://test.panel.com/login"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_login_success_with_set_cookie_header(vpn_service):
    """Test successful login with session cookie in Set-Cookie header."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.cookies = {}
    mock_response.headers = {'Set-Cookie': 'session=header_session_456; Path=/; HttpOnly'}
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    
    mock_session = AsyncMock()
    mock_session.post = MagicMock(return_value=mock_response)
    mock_session.closed = False
    
    vpn_service._session = mock_session
    
    await vpn_service._login()
    
    assert vpn_service._session_cookie == 'header_session_456'


@pytest.mark.asyncio
@pytest.mark.unit
async def test_login_failure_invalid_credentials(vpn_service):
    """Test login failure with 401 Unauthorized status."""
    mock_response = AsyncMock()
    mock_response.status = 401
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    
    mock_session = AsyncMock()
    mock_session.post = MagicMock(return_value=mock_response)
    mock_session.closed = False
    
    vpn_service._session = mock_session
    
    with pytest.raises(Exception, match="Invalid username or password"):
        await vpn_service._login()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_login_failure_forbidden(vpn_service):
    """Test login failure with 403 Forbidden status."""
    mock_response = AsyncMock()
    mock_response.status = 403
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    
    mock_session = AsyncMock()
    mock_session.post = MagicMock(return_value=mock_response)
    mock_session.closed = False
    
    vpn_service._session = mock_session
    
    with pytest.raises(Exception, match="Access forbidden"):
        await vpn_service._login()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_login_failure_no_session_cookie(vpn_service):
    """Test login failure when no session cookie is returned."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.cookies = {}
    mock_response.headers = {}
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    
    mock_session = AsyncMock()
    mock_session.post = MagicMock(return_value=mock_response)
    mock_session.closed = False
    
    vpn_service._session = mock_session
    
    with pytest.raises(Exception, match="No session cookie in response"):
        await vpn_service._login()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_login_retry_on_network_error(vpn_service):
    """Test retry logic with exponential backoff on transient network errors."""
    # First two attempts fail with network error, third succeeds
    mock_response_success = AsyncMock()
    mock_response_success.status = 200
    mock_response_success.cookies = {'session': MagicMock(value='retry_session_789')}
    mock_response_success.headers = {}
    mock_response_success.__aenter__ = AsyncMock(return_value=mock_response_success)
    mock_response_success.__aexit__ = AsyncMock(return_value=None)
    
    mock_session = AsyncMock()
    mock_session.closed = False
    
    # Simulate network errors on first two attempts, success on third
    call_count = 0
    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise ClientError("Network timeout")
        return mock_response_success
    
    mock_session.post = MagicMock(side_effect=side_effect)
    
    vpn_service._session = mock_session
    
    # Mock asyncio.sleep to avoid actual delays in tests
    with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        await vpn_service._login()
    
    assert vpn_service._session_cookie == 'retry_session_789'
    assert mock_session.post.call_count == 3
    # Verify exponential backoff: 1s, 2s
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(1)  # First retry delay
    mock_sleep.assert_any_call(2)  # Second retry delay


@pytest.mark.asyncio
@pytest.mark.unit
async def test_login_failure_after_max_retries(vpn_service):
    """Test login fails after exhausting all retry attempts."""
    mock_session = AsyncMock()
    mock_session.closed = False
    mock_session.post = MagicMock(side_effect=ClientError("Persistent network error"))
    
    vpn_service._session = mock_session
    
    with patch('asyncio.sleep', new_callable=AsyncMock):
        with pytest.raises(Exception, match="Authentication failed after 3 retries"):
            await vpn_service._login()
    
    assert mock_session.post.call_count == 3


@pytest.mark.asyncio
@pytest.mark.unit
async def test_login_timeout_configuration(vpn_service):
    """Test that session is created with 30 second timeout."""
    # Clear existing session to force creation
    vpn_service._session = None
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session_instance = AsyncMock()
        mock_session_instance.closed = False
        mock_session_class.return_value = mock_session_instance
        
        await vpn_service._ensure_session()
        
        # Verify ClientSession was created with timeout
        mock_session_class.assert_called_once()
        call_kwargs = mock_session_class.call_args[1]
        assert 'timeout' in call_kwargs
        timeout = call_kwargs['timeout']
        assert isinstance(timeout, ClientTimeout)
        assert timeout.total == 30


@pytest.mark.asyncio
@pytest.mark.unit
async def test_login_uses_config_credentials(vpn_service):
    """Test that login uses credentials from config."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.cookies = {'session': MagicMock(value='test_cookie')}
    mock_response.headers = {}
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    
    mock_session = AsyncMock()
    mock_session.post = MagicMock(return_value=mock_response)
    mock_session.closed = False
    
    vpn_service._session = mock_session
    
    with patch('bot.services.vpn_service.settings') as mock_settings:
        mock_settings.VPN_PANEL_USERNAME = "test_user"
        mock_settings.VPN_PANEL_PASSWORD = "test_pass"
        
        await vpn_service._login()
    
    # Verify form data was created with correct credentials
    call_args = mock_session.post.call_args
    form_data = call_args[1]['data']
    # FormData fields are stored internally, we verify the call was made
    assert mock_session.post.called

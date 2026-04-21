"""
Tests for API-based client creation (_create_user_api method).

This test file verifies that the new API-based client creation method
works correctly and falls back to direct DB access when needed.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from bot.services.vpn_service import VPNService


@pytest.mark.asyncio
async def test_create_user_api_success():
    """Test successful client creation via API."""
    service = VPNService()
    service.mock_mode = False
    service._session_cookie = "test_session_cookie"
    
    # Mock _login
    service._login = AsyncMock()
    
    # Mock _get_inbound_id
    service._get_inbound_id = MagicMock(return_value=1)
    
    # Mock database connection for port retrieval
    with patch('bot.services.vpn_service._db_connect') as mock_db:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (443,)
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn
        
        # Mock aiohttp session
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='{"success": true}')
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.closed = False
        
        service._session = mock_session
        
        # Call the method
        result = await service._create_user_api("test_user", 30, 50)
        
        # Verify result structure
        assert "uuid" in result
        assert "subscription_url" in result
        assert "expiry_date" in result
        assert "vless://" in result["subscription_url"]
        assert "test_user" not in result["subscription_url"]  # Email not in URL
        
        # Verify _login was called
        service._login.assert_called_once()
        
        # Verify API was called
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert "/panel/api/inbounds/addClient" in call_args[0][0]
        
    await service.close()


@pytest.mark.asyncio
async def test_create_user_api_fallback_on_error():
    """Test fallback to direct DB when API fails."""
    service = VPNService()
    service.mock_mode = False
    
    # Mock _login to fail
    service._login = AsyncMock(side_effect=Exception("API unavailable"))
    
    # Mock _create_user_direct_db
    expected_result = {
        "uuid": "test-uuid",
        "subscription_url": "vless://test",
        "expiry_date": "2026-05-21"
    }
    
    with patch.object(service, '_create_user_direct_db', return_value=expected_result):
        result = await service._create_user_api("test_user", 30, 50)
        
        # Verify fallback was used
        assert result == expected_result
    
    await service.close()


@pytest.mark.asyncio
async def test_create_user_api_mock_mode():
    """Test API method in mock mode."""
    service = VPNService()
    service.mock_mode = True
    
    result = await service._create_user_api("test_user", 30, 50)
    
    # Verify mock result structure
    assert "uuid" in result
    assert "subscription_url" in result
    assert "expiry_date" in result
    assert "MOCK" in result["subscription_url"]
    
    await service.close()


@pytest.mark.asyncio
async def test_create_user_calls_api_method():
    """Test that create_user now calls _create_user_api."""
    service = VPNService()
    service.mock_mode = True
    
    # Mock _create_user_api
    expected_result = {
        "uuid": "test-uuid",
        "subscription_url": "vless://test",
        "expiry_date": "2026-05-21"
    }
    service._create_user_api = AsyncMock(return_value=expected_result)
    
    result = await service.create_user("test_user", 30, 50)
    
    # Verify _create_user_api was called
    service._create_user_api.assert_called_once_with("test_user", 30, 50)
    assert result == expected_result
    
    await service.close()


@pytest.mark.asyncio
async def test_create_user_api_logs_request_and_response():
    """Test that API calls are logged for debugging."""
    service = VPNService()
    service.mock_mode = False
    service._session_cookie = "test_session_cookie"
    
    # Mock _login
    service._login = AsyncMock()
    
    # Mock _get_inbound_id
    service._get_inbound_id = MagicMock(return_value=1)
    
    # Mock database connection
    with patch('bot.services.vpn_service._db_connect') as mock_db:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (443,)
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn
        
        # Mock aiohttp session
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='{"success": true}')
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.closed = False
        
        service._session = mock_session
        
        # Capture logs
        with patch('bot.services.vpn_service.logger') as mock_logger:
            await service._create_user_api("test_user", 30, 50)
            
            # Verify debug logs were called
            debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
            assert any("API Request:" in call for call in debug_calls)
            assert any("API Response:" in call for call in debug_calls)
    
    await service.close()

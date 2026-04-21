"""Unit tests for VPNService HTTP client and session management."""
import pytest
import aiohttp
from bot.services.vpn_service import VPNService


@pytest.mark.asyncio
async def test_ensure_session_creates_new_session():
    """Test that _ensure_session creates a new aiohttp session."""
    service = VPNService()
    
    # Initially, session should be None
    assert service._session is None
    
    # Call _ensure_session
    session = await service._ensure_session()
    
    # Session should be created
    assert session is not None
    assert isinstance(session, aiohttp.ClientSession)
    assert service._session is session
    
    # Cleanup
    await service.close()


@pytest.mark.asyncio
async def test_ensure_session_reuses_existing_session():
    """Test that _ensure_session reuses an existing session."""
    service = VPNService()
    
    # Create first session
    session1 = await service._ensure_session()
    
    # Call again - should return same session
    session2 = await service._ensure_session()
    
    assert session1 is session2
    
    # Cleanup
    await service.close()


@pytest.mark.asyncio
async def test_ensure_session_has_timeout():
    """Test that session is created with proper timeout."""
    service = VPNService()
    
    session = await service._ensure_session()
    
    # Check timeout is set to 30 seconds
    assert session.timeout.total == 30
    
    # Cleanup
    await service.close()


@pytest.mark.asyncio
async def test_close_closes_session():
    """Test that close() properly closes the aiohttp session."""
    service = VPNService()
    
    # Create session
    await service._ensure_session()
    assert service._session is not None
    assert not service._session.closed
    
    # Close session
    await service.close()
    
    # Session should be closed and cleared
    assert service._session is None
    assert service._session_cookie is None


@pytest.mark.asyncio
async def test_close_handles_no_session():
    """Test that close() handles case when no session exists."""
    service = VPNService()
    
    # Close without creating session - should not raise error
    await service.close()
    
    assert service._session is None


@pytest.mark.asyncio
async def test_close_handles_already_closed_session():
    """Test that close() handles already closed session."""
    service = VPNService()
    
    # Create and close session
    await service._ensure_session()
    await service.close()
    
    # Close again - should not raise error
    await service.close()
    
    assert service._session is None


@pytest.mark.asyncio
async def test_session_cookie_initialized_as_none():
    """Test that _session_cookie is initialized as None."""
    service = VPNService()
    
    assert service._session_cookie is None
    
    # Cleanup
    await service.close()

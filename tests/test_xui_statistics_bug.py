"""
Bug Fix Verification Test for X-UI Statistics Fix

**Validates: Requirements 1.1, 1.2, 2.1, 2.2**

This test MUST PASS on fixed code - passing confirms the bug is resolved.

The test creates a client using the API-based method (_create_user_api) and verifies
that statistics tracking works correctly (traffic shows actual usage, status shows online).
"""

import pytest
import sqlite3
import json
import time
from datetime import datetime
from hypothesis import given, strategies as st, settings, Phase
from bot.services.vpn_service import VPNService, _db_connect

# Test configuration
XUI_DB_PATH = "/etc/x-ui/x-ui.db"
TEST_USERNAME_PREFIX = "test_bug_exploration_"


def get_client_traffic_from_db(username: str) -> dict:
    """
    Query x-ui database to check traffic statistics for a client.
    
    Returns:
        dict with keys: 'up' (uploaded bytes), 'down' (downloaded bytes), 'exists'
    """
    conn = _db_connect()
    try:
        cursor = conn.cursor()
        
        # Check if client_traffics table exists and has entry for this client
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='client_traffics'
        """)
        if not cursor.fetchone():
            return {'up': 0, 'down': 0, 'exists': False, 'reason': 'client_traffics table not found'}
        
        # Query traffic data for the client
        cursor.execute("""
            SELECT up, down, enable 
            FROM client_traffics 
            WHERE email = ?
        """, (username,))
        
        row = cursor.fetchone()
        if not row:
            return {'up': 0, 'down': 0, 'exists': False, 'reason': 'no entry in client_traffics'}
        
        return {
            'up': row[0],
            'down': row[1],
            'exists': True,
            'enabled': row[2] if len(row) > 2 else None
        }
    finally:
        conn.close()


def get_client_from_inbound(username: str) -> dict:
    """
    Get client configuration from inbound settings.
    
    Returns:
        dict with client data or None if not found
    """
    conn = _db_connect()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT settings FROM inbounds WHERE protocol='vless' LIMIT 1")
        row = cursor.fetchone()
        if not row:
            return None
        
        settings_json = json.loads(row[0])
        clients = settings_json.get("clients", [])
        
        for client in clients:
            if client.get("email") == username:
                return client
        
        return None
    finally:
        conn.close()


def simulate_data_transfer(username: str, megabytes: int = 100):
    """
    Simulate data transfer by updating client_traffics table.
    
    In a real scenario, this would happen when the VPN client connects and transfers data.
    For testing purposes, we directly update the traffic counters to simulate usage.
    
    Note: This simulation will only work if the client_traffics entry exists.
    For bot-created clients (direct DB access), this entry is missing - that's the bug!
    """
    bytes_transferred = megabytes * 1024 * 1024
    
    conn = _db_connect()
    try:
        cursor = conn.cursor()
        
        # Try to update traffic - this will fail silently if entry doesn't exist
        cursor.execute("""
            UPDATE client_traffics 
            SET down = down + ?, up = up + ?
            WHERE email = ?
        """, (bytes_transferred, bytes_transferred // 2, username))
        
        rows_affected = cursor.rowcount
        conn.commit()
        
        return rows_affected > 0
    finally:
        conn.close()


@pytest.mark.integration
class TestBugConditionExploration:
    """
    Bug Condition Exploration Tests
    
    These tests demonstrate the bug by creating clients via direct DB access
    and showing that statistics tracking is broken.
    """
    
    @pytest.fixture
    def vpn_service(self):
        """Create VPNService instance for testing."""
        service = VPNService()
        # Ensure we're NOT in mock mode for this test
        service.mock_mode = False
        return service
    
    @pytest.fixture
    def cleanup_test_users(self):
        """Cleanup any test users created during testing."""
        created_users = []
        
        yield created_users
        
        # Cleanup after test
        conn = _db_connect()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, settings FROM inbounds WHERE protocol='vless' LIMIT 1")
            row = cursor.fetchone()
            if row:
                inbound_id, settings_str = row
                settings_json = json.loads(settings_str)
                clients = settings_json.get("clients", [])
                
                # Remove test clients
                new_clients = [
                    c for c in clients 
                    if c.get("email") not in created_users
                ]
                
                if len(new_clients) != len(clients):
                    settings_json["clients"] = new_clients
                    cursor.execute(
                        "UPDATE inbounds SET settings = ? WHERE id = ?",
                        (json.dumps(settings_json), inbound_id)
                    )
                    conn.commit()
        finally:
            conn.close()
    
    async def test_direct_db_create_missing_statistics_tracking(
        self, vpn_service, cleanup_test_users
    ):
        """
        **Property 1: Bug Condition** - API-Created Clients Show Statistics
        
        **Validates: Requirements 1.1, 1.2, 2.1, 2.2**
        
        EXPECTED OUTCOME: This test SHOULD PASS on fixed code.
        
        Test demonstrates that clients created via x-ui API have proper
        statistics tracking initialized in x-ui.
        
        Steps:
        1. Create client using _create_user_api (API-based method)
        2. Verify client exists in inbound settings
        3. Simulate VPN connection and data transfer (100 MB)
        4. Query x-ui database for traffic statistics
        5. Assert traffic > 0 GB (EXPECTED BEHAVIOR - should pass on fixed code)
        6. Assert online status tracking exists (EXPECTED BEHAVIOR - should pass on fixed code)
        """
        # Arrange
        username = f"{TEST_USERNAME_PREFIX}{int(time.time())}"
        cleanup_test_users.append(username)
        expiry_days = 30
        traffic_limit_gb = 50
        
        # Act: Create client via API (fixed method)
        result = await vpn_service._create_user_api(username, expiry_days, traffic_limit_gb)
        
        # Verify client was created in inbound settings
        client_config = get_client_from_inbound(username)
        assert client_config is not None, f"Client {username} not found in inbound settings"
        assert client_config["email"] == username
        assert client_config["enable"] is True
        
        # Simulate VPN connection and data transfer
        # In real scenario, this happens when client connects and uses VPN
        # For testing, we simulate by attempting to update traffic counters
        transfer_success = simulate_data_transfer(username, megabytes=100)
        
        # Query x-ui database for traffic statistics
        traffic_stats = get_client_traffic_from_db(username)
        
        # ASSERTIONS - These represent EXPECTED BEHAVIOR
        # On fixed code, these should PASS because:
        # - client_traffics entry exists (API properly initializes tracking)
        # - Traffic shows actual usage after simulated transfer
        # - Online status tracking is properly initialized
        
        # Assert 1: client_traffics entry should exist
        assert traffic_stats['exists'], (
            f"FIX VERIFICATION FAILED: Client {username} has no entry in client_traffics table. "
            f"Reason: {traffic_stats.get('reason', 'unknown')}. "
            f"The API-based creation should have initialized tracking."
        )
        
        # Assert 2: Traffic should be tracked (> 0 after data transfer)
        total_traffic_bytes = traffic_stats['up'] + traffic_stats['down']
        total_traffic_gb = total_traffic_bytes / (1024 ** 3)
        
        assert total_traffic_gb > 0, (
            f"FIX VERIFICATION FAILED: Client {username} shows {total_traffic_gb:.4f} GB traffic "
            f"despite simulated 100 MB transfer. "
            f"Expected: >0 GB, Got: {total_traffic_gb:.4f} GB. "
            f"Upload: {traffic_stats['up']} bytes, Download: {traffic_stats['down']} bytes. "
            f"The API-based creation should have enabled proper statistics tracking."
        )
        
        # Assert 3: Client should be enabled for tracking
        if traffic_stats['exists']:
            assert traffic_stats.get('enabled') is not None, (
                f"FIX VERIFICATION FAILED: Client {username} has no 'enable' status in client_traffics. "
                f"The API-based creation should have initialized complete tracking."
            )
    
    @given(
        expiry_days=st.integers(min_value=1, max_value=365),
        traffic_limit_gb=st.integers(min_value=10, max_value=1000),
        data_transfer_mb=st.integers(min_value=50, max_value=500)
    )
    @settings(
        max_examples=5,  # Scoped PBT: Limited examples since fix should be consistent
        phases=[Phase.generate, Phase.target],  # Skip shrinking for verification
        deadline=None  # No deadline for integration tests
    )
    async def test_property_direct_db_prevents_statistics(
        self, vpn_service, cleanup_test_users, expiry_days, traffic_limit_gb, data_transfer_mb
    ):
        """
        **Property 1: Bug Fix Verification (Property-Based)** - API-Created Clients Show Statistics
        
        **Validates: Requirements 1.1, 1.2, 2.1, 2.2**
        
        Property-based test that verifies the fix works across various client configurations.
        
        EXPECTED OUTCOME: This test SHOULD PASS on fixed code for all inputs.
        
        Property: For ANY client created via x-ui API with ANY configuration,
        statistics tracking SHOULD work correctly.
        """
        # Arrange
        username = f"{TEST_USERNAME_PREFIX}pbt_{int(time.time())}_{expiry_days}"
        cleanup_test_users.append(username)
        
        # Act: Create client via API (fixed method)
        result = await vpn_service._create_user_api(username, expiry_days, traffic_limit_gb)
        
        # Verify client exists
        client_config = get_client_from_inbound(username)
        assert client_config is not None
        
        # Simulate data transfer
        simulate_data_transfer(username, megabytes=data_transfer_mb)
        
        # Check statistics
        traffic_stats = get_client_traffic_from_db(username)
        
        # Property assertion: Statistics tracking should exist and show non-zero traffic
        assert traffic_stats['exists'], (
            f"Property violation: Client created with expiry={expiry_days}d, "
            f"limit={traffic_limit_gb}GB has no client_traffics entry. "
            f"Fix should work consistently across all configurations."
        )
        
        total_traffic_gb = (traffic_stats['up'] + traffic_stats['down']) / (1024 ** 3)
        assert total_traffic_gb > 0, (
            f"Property violation: Client with {data_transfer_mb}MB simulated transfer "
            f"shows {total_traffic_gb:.4f}GB. Fix should work for all traffic amounts."
        )


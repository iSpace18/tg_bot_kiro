# X-UI Statistics Fix Bugfix Design

## Overview

The bug occurs because the bot bypasses x-ui's API and directly manipulates the SQLite database. This prevents x-ui from initializing internal tracking structures (client_traffics table, in-memory state) needed for statistics. The fix involves replacing direct database access with x-ui API calls (`/panel/api/inbounds/addClient`, `/panel/api/inbounds/delClient`) while maintaining authentication via session cookies. This ensures x-ui properly tracks all bot-created clients.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when clients are created/deleted via direct database manipulation instead of x-ui API
- **Property (P)**: The desired behavior - clients created via API show proper statistics (online status, traffic usage)
- **Preservation**: Existing VPN connectivity, subscription URL format, mock mode, and manually-created client statistics must remain unchanged
- **VPNService**: The class in `bot/services/vpn_service.py` that manages client lifecycle
- **_create_user_sync**: Synchronous method that creates clients by directly writing to x-ui.db
- **_delete_user_sync**: Synchronous method that deletes clients by directly modifying x-ui.db
- **client_traffics**: x-ui database table that stores per-client traffic statistics (not initialized by direct DB writes)
- **Session Cookie**: Authentication token obtained by logging into x-ui panel, required for API calls

## Bug Details

### Bug Condition

The bug manifests when the bot creates or deletes clients using direct SQLite database manipulation. The `_create_user_sync` method directly modifies the `inbounds.settings` JSON field, and `_delete_user_sync` directly removes clients from this field. This bypasses x-ui's internal initialization logic that creates tracking entries in the `client_traffics` table and updates in-memory state.

**Formal Specification:**
```
FUNCTION isBugCondition(operation)
  INPUT: operation of type ClientOperation (create or delete)
  OUTPUT: boolean
  
  RETURN operation.method IN ['_create_user_sync', '_delete_user_sync']
         AND operation.uses_direct_db_access == True
         AND NOT operation.uses_xui_api == True
END FUNCTION
```

### Examples

- **Create via direct DB**: Bot calls `_create_user_sync("user123", 30, 50)` → Client appears in x-ui but shows 0 GB traffic and offline status even when connected
- **Delete via direct DB**: Bot calls `_delete_user_sync("user123")` → Client removed from inbound settings but tracking entries remain in client_traffics table
- **Create via API (expected)**: Bot calls x-ui API `/panel/api/inbounds/addClient` → Client appears with proper tracking, shows online status and real-time traffic
- **Manual creation (works correctly)**: Admin creates client through x-ui web interface → Statistics work perfectly because x-ui's internal logic runs

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- VPN connections must continue to work with VLESS-Reality-TCP-Vision protocol
- Subscription URLs must maintain correct Reality parameters (pbk, fp, sni, sid, spx, flow)
- Mock mode (`VPN_MOCK_MODE=True`) must continue to function for testing
- Manually created clients (through x-ui web interface) must continue showing statistics correctly
- Existing VPN connections for other clients must not be interrupted during create/delete operations
- The bot's async interface (`create_user`, `delete_user`, `get_client_info`) must remain unchanged

**Scope:**
All operations that do NOT involve creating or deleting clients should be completely unaffected by this fix. This includes:
- Reading client information from the database
- Mock mode operations (testing without real VPN panel)
- Configuration loading and validation
- Subscription URL generation logic
- Xray process restart mechanism

## Hypothesized Root Cause

Based on the bug description and code analysis, the root cause is:

1. **Bypassing x-ui's Initialization Logic**: Direct database writes skip x-ui's client creation workflow, which includes:
   - Creating entries in the `client_traffics` table for traffic tracking
   - Initializing in-memory state for real-time statistics
   - Setting up monitoring hooks for connection status

2. **Missing API Authentication**: The bot doesn't implement x-ui API authentication (session cookies or API tokens), forcing it to use direct database access as a workaround

3. **No API Integration**: The codebase has no HTTP client setup for x-ui API calls, only direct SQLite connections

4. **State Synchronization Issues**: Direct database modifications don't trigger x-ui's internal event handlers that update statistics tracking

## Correctness Properties

Property 1: Bug Condition - API-Created Clients Show Statistics

_For any_ client creation or deletion operation performed via x-ui API endpoints (addClient/delClient), the x-ui web interface SHALL display accurate real-time statistics including online status and traffic usage (GB downloaded/uploaded).

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Preservation - VPN Connectivity and Existing Features

_For any_ operation that is NOT client creation or deletion (reading client info, mock mode, subscription URL generation), the fixed code SHALL produce exactly the same behavior as the original code, preserving VPN connectivity, URL format, and all existing functionality.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `bot/services/vpn_service.py`

**Class**: `VPNService`

**Specific Changes**:

1. **Add HTTP Client and Session Management**:
   - Import `aiohttp` for async HTTP requests
   - Add `_session: Optional[aiohttp.ClientSession]` attribute
   - Add `_session_cookie: Optional[str]` attribute for authentication
   - Add `_ensure_session()` method to create/reuse aiohttp session

2. **Implement Authentication**:
   - Add `_login()` async method that:
     - POSTs to `/login` with `username` and `password` from config
     - Extracts session cookie from response headers
     - Stores cookie in `_session_cookie` for subsequent API calls
     - Handles authentication failures with proper error messages

3. **Replace _create_user_sync with API Call**:
   - Rename `_create_user_sync` to `_create_user_direct_db` (keep as fallback)
   - Create new `_create_user_api` async method that:
     - Calls `_login()` to get authenticated session
     - POSTs to `/panel/api/inbounds/addClient` with JSON payload:
       ```json
       {
         "id": inbound_id,
         "settings": json.dumps({
           "clients": [{
             "id": uuid,
             "email": username,
             "flow": "xtls-rprx-vision",
             "enable": true,
             "expiryTime": expiry_ts,
             "totalGB": total_gb,
             "limitIp": 1
           }]
         })
       }
       ```
     - Handles API errors with fallback to direct DB method
     - Returns same dict format as before (uuid, subscription_url, expiry_date)

4. **Replace _delete_user_sync with API Call**:
   - Rename `_delete_user_sync` to `_delete_user_direct_db` (keep as fallback)
   - Create new `_delete_user_api` async method that:
     - Calls `_login()` to get authenticated session
     - POSTs to `/panel/api/inbounds/delClient` with JSON payload:
       ```json
       {
         "id": inbound_id,
         "email": username
       }
       ```
     - Handles API errors with fallback to direct DB method
     - Returns boolean success status

5. **Update Public Methods**:
   - Modify `create_user()` to call `_create_user_api()` instead of running `_create_user_sync` in executor
   - Modify `delete_user()` to call `_delete_user_api()` instead of running `_delete_user_sync` in executor
   - Keep mock mode checks at the beginning of each method

6. **Add Error Handling and Logging**:
   - Log all API requests and responses for debugging
   - Implement retry logic for transient network errors
   - Fallback to direct DB access if API is unavailable (with warning log)
   - Add timeout configuration for HTTP requests (30 seconds default)

7. **Add Cleanup Method**:
   - Add `async def close()` method to properly close aiohttp session
   - Call this in bot shutdown sequence

### API Endpoint Details

Based on x-ui panel structure, the expected endpoints are:

- **Login**: `POST /login`
  - Body: `username=<user>&password=<pass>` (form-encoded)
  - Response: Sets `session` cookie in headers
  
- **Add Client**: `POST /panel/api/inbounds/addClient`
  - Headers: `Cookie: session=<token>`
  - Body: JSON with `id` (inbound_id) and `settings` (client config)
  - Response: JSON with `success: true/false`

- **Delete Client**: `POST /panel/api/inbounds/delClient`
  - Headers: `Cookie: session=<token>`
  - Body: JSON with `id` (inbound_id) and `email` (username)
  - Response: JSON with `success: true/false`

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code (direct DB access), then verify the fix works correctly (API access) and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that direct database access causes missing statistics.

**Test Plan**: Create clients using the current `_create_user_sync` method (direct DB), then check x-ui web interface to verify statistics are missing. Run these tests on the UNFIXED code to observe failures and confirm root cause.

**Test Cases**:
1. **Direct DB Create Test**: Create client via `_create_user_sync`, connect VPN, check x-ui shows 0 GB traffic (will fail - demonstrates bug)
2. **Direct DB Delete Test**: Delete client via `_delete_user_sync`, check if client_traffics entry remains (will fail - demonstrates incomplete cleanup)
3. **Manual Create Comparison**: Create client manually through x-ui web interface, verify statistics work (will pass - confirms x-ui itself works)
4. **Connection Status Test**: Create client via direct DB, establish VPN connection, check x-ui shows "offline" (will fail - demonstrates status tracking bug)

**Expected Counterexamples**:
- Bot-created clients show 0 GB traffic even after data transfer
- Bot-created clients show "offline" status even when connected
- Possible causes: missing client_traffics entries, uninitialized in-memory state, no event handler triggers

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds (client create/delete operations), the fixed function produces the expected behavior (proper statistics tracking).

**Pseudocode:**
```
FOR ALL operation WHERE isBugCondition(operation) DO
  result := perform_operation_via_api(operation)
  ASSERT statistics_are_tracked(result)
  ASSERT online_status_is_accurate(result)
END FOR
```

**Test Plan**: After implementing API-based methods, create clients via `_create_user_api`, connect VPN, and verify x-ui web interface shows:
- Accurate traffic usage (GB downloaded/uploaded)
- Correct online/offline status
- Real-time statistics updates

**Test Cases**:
1. **API Create with Traffic Test**: Create client via API, transfer 100 MB data, verify x-ui shows ~100 MB usage
2. **API Create with Connection Test**: Create client via API, establish VPN connection, verify x-ui shows "online" status
3. **API Delete Test**: Delete client via API, verify client_traffics entry is removed and no stale data remains
4. **Multiple Clients Test**: Create 5 clients via API, verify all show independent statistics correctly

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold (non-create/delete operations, mock mode, existing features), the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL operation WHERE NOT isBugCondition(operation) DO
  ASSERT original_behavior(operation) = fixed_behavior(operation)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for VPN connectivity, subscription URLs, and mock mode, then write property-based tests capturing that behavior.

**Test Cases**:
1. **VPN Connectivity Preservation**: Create clients via API, verify VPN connections work with VLESS-Reality protocol (same as before)
2. **Subscription URL Preservation**: Generate subscription URLs, verify they contain correct Reality parameters (pbk, fp, sni, sid, spx, flow)
3. **Mock Mode Preservation**: Run bot in mock mode, verify all operations work without real VPN panel (same as before)
4. **Manual Client Preservation**: Create clients manually through x-ui, verify their statistics continue working correctly
5. **Existing Connection Preservation**: Create/delete clients via API while other clients are connected, verify no interruptions
6. **get_client_info Preservation**: Call `get_client_info()` for various clients, verify it returns same data structure as before

### Unit Tests

- Test `_login()` method with valid/invalid credentials
- Test `_create_user_api()` with various expiry days and traffic limits
- Test `_delete_user_api()` with existing/non-existing clients
- Test error handling when x-ui API is unavailable (fallback to direct DB)
- Test session cookie extraction and reuse
- Test mock mode continues to work correctly

### Property-Based Tests

- Generate random client configurations (username, expiry, traffic limit) and verify API creates them correctly
- Generate random sequences of create/delete operations and verify statistics remain consistent
- Generate random VPN connection patterns and verify traffic tracking accuracy
- Test that all non-create/delete operations produce identical results before and after fix

### Integration Tests

- Test full bot flow: user requests trial → client created via API → VPN connects → statistics visible in x-ui
- Test client deletion flow: user subscription expires → bot deletes via API → client removed from x-ui completely
- Test concurrent operations: multiple users creating/deleting clients simultaneously
- Test x-ui panel restart: verify bot reconnects and continues working
- Test network failures: verify fallback to direct DB when API is unreachable

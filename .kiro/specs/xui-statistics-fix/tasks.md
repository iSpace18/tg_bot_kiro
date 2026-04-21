# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Direct DB Access Prevents Statistics Tracking
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: For deterministic bugs, scope the property to the concrete failing case(s) to ensure reproducibility
  - Test implementation details from Bug Condition in design:
    - Create a test client using current `_create_user_sync()` method (direct DB access)
    - Simulate VPN connection and data transfer (e.g., 100 MB)
    - Query x-ui web interface or database to check displayed traffic statistics
    - Assert that traffic usage is greater than 0 GB (expected behavior)
    - Assert that online status is "online" when connected (expected behavior)
  - The test assertions should match the Expected Behavior Properties from design:
    - Property: Clients created via API show proper statistics (online status, traffic usage)
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
    - Expected failure: Traffic shows 0 GB despite data transfer
    - Expected failure: Status shows "offline" despite active connection
  - Document counterexamples found to understand root cause:
    - Record specific traffic values observed (e.g., "Expected >0 GB, got 0 GB")
    - Record connection status observed (e.g., "Expected 'online', got 'offline'")
    - Check if `client_traffics` table entries exist for bot-created clients
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 2.1, 2.2_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - VPN Connectivity and Existing Features Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs:
    - Create client via current `_create_user_sync()` method
    - Test VPN connection with VLESS-Reality protocol
    - Verify connection succeeds and data flows correctly
    - Generate subscription URL and verify format/parameters
    - Test mock mode operations (`VPN_MOCK_MODE=True`)
    - Test `get_client_info()` method returns expected data structure
    - Create client manually through x-ui web interface, verify statistics work
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements:
    - **Property**: VPN connections work with VLESS-Reality-TCP-Vision protocol
    - **Property**: Subscription URLs contain correct Reality parameters (pbk, fp, sni, sid, spx, flow)
    - **Property**: Mock mode functions correctly without real VPN panel
    - **Property**: Manually created clients show statistics correctly
    - **Property**: Existing connections remain uninterrupted during create/delete operations
    - **Property**: `get_client_info()` returns consistent data structure
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3. Fix for x-ui statistics tracking via API integration

  - [x] 3.1 Add HTTP client and session management to VPNService
    - Import `aiohttp` library for async HTTP requests
    - Add `_session: Optional[aiohttp.ClientSession]` attribute to VPNService class
    - Add `_session_cookie: Optional[str]` attribute for authentication token storage
    - Implement `_ensure_session()` method to create/reuse aiohttp session with proper timeout (30s)
    - Implement `async def close()` method to properly close aiohttp session on shutdown
    - Add session cleanup to bot shutdown sequence
    - _Bug_Condition: isBugCondition(operation) where operation.uses_direct_db_access == True_
    - _Expected_Behavior: Operations use x-ui API with proper authentication_
    - _Preservation: Existing async interface and mock mode unchanged_
    - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 3.2 Implement x-ui API authentication
    - Create `_login()` async method that:
      - POSTs to `{VPN_PANEL_URL}/login` with form-encoded credentials
      - Uses `username=VPN_PANEL_USERNAME&password=VPN_PANEL_PASSWORD` from config
      - Extracts `session` cookie from response headers
      - Stores cookie in `_session_cookie` for subsequent API calls
      - Handles authentication failures with clear error messages
      - Logs successful authentication for debugging
    - Add retry logic for transient network errors (3 retries with exponential backoff)
    - Add timeout configuration for login requests (30 seconds)
    - _Bug_Condition: isBugCondition(operation) where operation.uses_direct_db_access == True_
    - _Expected_Behavior: Bot authenticates with x-ui API using session cookies_
    - _Preservation: Configuration loading and validation unchanged_
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.3 Replace _create_user_sync with API-based client creation
    - Rename existing `_create_user_sync` to `_create_user_direct_db` (keep as fallback)
    - Create new `_create_user_api` async method that:
      - Calls `_login()` to obtain authenticated session
      - Retrieves inbound_id using `_get_inbound_id()`
      - Generates client UUID and calculates expiry timestamp
      - POSTs to `{VPN_PANEL_URL}/panel/api/inbounds/addClient` with JSON payload:
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
      - Includes `Cookie: session=<token>` header for authentication
      - Handles API errors with fallback to `_create_user_direct_db` (with warning log)
      - Returns same dict format: `{uuid, subscription_url, expiry_date}`
      - Logs all API requests and responses for debugging
    - Update `create_user()` method to call `_create_user_api()` instead of running `_create_user_sync` in executor
    - Preserve mock mode check at beginning of method
    - _Bug_Condition: isBugCondition(operation) where operation.method == '_create_user_sync'_
    - _Expected_Behavior: Clients created via API show proper statistics (online status, traffic usage)_
    - _Preservation: Subscription URL format, VPN connectivity, mock mode unchanged_
    - _Requirements: 2.1, 2.2, 3.1, 3.2, 3.3, 3.5_

  - [x] 3.4 Replace _delete_user_sync with API-based client deletion
    - Rename existing `_delete_user_sync` to `_delete_user_direct_db` (keep as fallback)
    - Create new `_delete_user_api` async method that:
      - Calls `_login()` to obtain authenticated session
      - Retrieves inbound_id using `_get_inbound_id()`
      - POSTs to `{VPN_PANEL_URL}/panel/api/inbounds/delClient` with JSON payload:
        ```json
        {
          "id": inbound_id,
          "email": username
        }
        ```
      - Includes `Cookie: session=<token>` header for authentication
      - Handles API errors with fallback to `_delete_user_direct_db` (with warning log)
      - Returns boolean success status
      - Logs all API requests and responses for debugging
    - Update `delete_user()` method to call `_delete_user_api()` instead of running `_delete_user_sync` in executor
    - Preserve mock mode check at beginning of method
    - _Bug_Condition: isBugCondition(operation) where operation.method == '_delete_user_sync'_
    - _Expected_Behavior: x-ui's internal state properly updated, client removed from all tracking_
    - _Preservation: Existing connections uninterrupted, mock mode unchanged_
    - _Requirements: 2.3, 3.3, 3.5_

  - [x] 3.5 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - API-Created Clients Show Statistics
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1:
      - Create client using new `_create_user_api()` method
      - Simulate VPN connection and data transfer (e.g., 100 MB)
      - Query x-ui web interface or database to check displayed traffic statistics
      - Assert traffic usage is greater than 0 GB
      - Assert online status is "online" when connected
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - Verify counterexamples from task 1 are resolved:
      - Traffic now shows actual usage (e.g., ">0 GB" instead of "0 GB")
      - Status now shows "online" when connected (instead of "offline")
      - `client_traffics` table entries exist for API-created clients
    - _Requirements: 2.1, 2.2_

  - [x] 3.6 Verify preservation tests still pass
    - **Property 2: Preservation** - VPN Connectivity and Existing Features Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2:
      - Test VPN connections work with VLESS-Reality-TCP-Vision protocol
      - Test subscription URLs contain correct Reality parameters
      - Test mock mode functions correctly
      - Test manually created clients show statistics correctly
      - Test existing connections remain uninterrupted
      - Test `get_client_info()` returns consistent data structure
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 4. Checkpoint - Ensure all tests pass
  - Run complete test suite (bug condition + preservation tests)
  - Verify all tests pass without errors
  - Review logs for any warnings or unexpected behavior
  - Test with real x-ui panel if available, or mock mode for validation
  - Ask the user if questions arise or manual verification is needed

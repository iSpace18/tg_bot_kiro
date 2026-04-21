# X-UI Statistics Bug Exploration Tests

## Overview

This directory contains bug condition exploration tests for the x-ui statistics tracking issue. These tests are designed to **FAIL on unfixed code** to prove the bug exists.

## Test Purpose

The test in `test_xui_statistics_bug.py` demonstrates that clients created via direct database manipulation (current `_create_user_sync` method) do not have proper statistics tracking in x-ui.

**Expected Outcome**: The test WILL FAIL, which is CORRECT behavior. The failure proves:
- Bot-created clients have no entry in `client_traffics` table
- Traffic shows 0 GB despite data transfer
- Online status tracking is missing

## Requirements

- pytest >= 7.4.3
- hypothesis >= 6.92.1
- Access to x-ui database at `/etc/x-ui/x-ui.db`

Install dependencies:
```bash
pip install -r requirements.txt
```

## Running Tests

### On Linux Server (with x-ui installed)

Run the integration test that requires real x-ui database:

```bash
# Run bug exploration test (expected to FAIL on unfixed code)
pytest tests/test_xui_statistics_bug.py --run-integration -v
```

### On Windows/Development Machine

The integration tests require access to the x-ui database which is only available on the Linux server. To run these tests:

1. SSH into the server where x-ui is installed
2. Navigate to the bot directory
3. Run the pytest command above

Alternatively, you can skip integration tests locally:

```bash
# Run only unit tests (skips integration tests)
pytest tests/ -v
```

## Test Structure

### `test_direct_db_create_missing_statistics_tracking`

**Property 1: Bug Condition** - Direct DB Access Prevents Statistics Tracking

**Validates: Requirements 1.1, 1.2, 2.1, 2.2**

This test:
1. Creates a client using `_create_user_sync()` (direct DB access)
2. Verifies client exists in inbound settings
3. Simulates VPN connection and data transfer (100 MB)
4. Queries x-ui database for traffic statistics
5. Asserts traffic > 0 GB (EXPECTED BEHAVIOR)
6. Asserts online status tracking exists (EXPECTED BEHAVIOR)

**Expected Result**: FAIL - Assertions will fail because:
- `client_traffics` entry doesn't exist (direct DB bypass)
- Traffic shows 0 GB despite simulated transfer
- No online status tracking

### `test_property_direct_db_prevents_statistics`

**Property 1: Bug Condition (Property-Based)** - Direct DB Access Prevents Statistics

**Validates: Requirements 1.1, 1.2, 2.1, 2.2**

Property-based test using Hypothesis that explores various client configurations (different expiry days, traffic limits, data transfer amounts) to demonstrate the bug is consistent across all inputs.

**Expected Result**: FAIL for all generated test cases - Bug affects all configurations.

## Counterexamples to Document

When the test fails (as expected), document these counterexamples:

1. **Missing client_traffics entry**: 
   - Client exists in inbound settings but has no entry in `client_traffics` table
   - Reason: Direct DB access bypasses x-ui's tracking initialization

2. **Zero traffic despite transfer**:
   - Expected: >0 GB after 100 MB simulated transfer
   - Got: 0 GB
   - Reason: No tracking entry to update

3. **Missing online status**:
   - Expected: "online" when connected
   - Got: No status tracking
   - Reason: x-ui's internal state not initialized

## After Fix Implementation

After implementing the fix (using x-ui API instead of direct DB access), this same test should PASS, confirming:
- Clients created via API have proper `client_traffics` entries
- Traffic is tracked correctly
- Online status is displayed accurately

## Notes

- DO NOT attempt to fix the test when it fails - the failure is expected and correct
- DO NOT attempt to fix the code during this exploration phase
- The test encodes the expected behavior and will validate the fix later
- Use `--run-integration` flag to run tests that require real x-ui database

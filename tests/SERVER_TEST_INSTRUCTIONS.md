# Running Tests on VPN Server

## Overview
The bug condition exploration tests require access to the real x-ui database and panel. These tests must be run on the actual Linux VPN server where x-ui is installed.

## Prerequisites
1. SSH access to the VPN server
2. x-ui panel installed and running
3. Python 3.8+ with pytest and hypothesis installed
4. Project files uploaded to the server

## Step 1: Upload Project to Server

### Option A: Using PowerShell Script (Windows)
```powershell
.\upload_to_server.ps1
```

### Option B: Manual Upload via SCP
```bash
scp -r . user@your-server-ip:/path/to/project/
```

## Step 2: SSH into Server
```bash
ssh user@your-server-ip
cd /path/to/project/
```

## Step 3: Install Test Dependencies
```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio hypothesis
```

## Step 4: Run Complete Test Suite

### Run All Tests (Bug Condition + Preservation)
```bash
pytest tests/test_xui_statistics_bug.py tests/test_xui_preservation.py --run-integration -v
```

### Run Only Bug Condition Tests
```bash
bash tests/run_bug_exploration.sh
```

### Run Only Preservation Tests
```bash
pytest tests/test_xui_preservation.py --run-integration -v
```

## Expected Results

### ✅ Success Scenario (All Tests Pass)
```
tests/test_xui_statistics_bug.py::TestBugConditionExploration::test_direct_db_create_missing_statistics_tracking PASSED
tests/test_xui_statistics_bug.py::TestBugConditionExploration::test_property_direct_db_prevents_statistics PASSED
tests/test_xui_preservation.py::TestPreservationProperties::test_vpn_connectivity_vless_reality_protocol PASSED
tests/test_xui_preservation.py::TestPreservationProperties::test_subscription_url_reality_parameters PASSED
tests/test_xui_preservation.py::TestPreservationProperties::test_mock_mode_operations PASSED
tests/test_xui_preservation.py::TestPreservationProperties::test_get_client_info_data_structure PASSED
tests/test_xui_preservation.py::TestPreservationProperties::test_property_subscription_url_format_consistency PASSED
tests/test_xui_preservation.py::TestPreservationProperties::test_property_client_creation_and_retrieval PASSED

8 passed
```

**This confirms:**
- ✓ Bug is fixed - API-based creation enables statistics tracking
- ✓ Traffic usage shows actual values (>0 GB after data transfer)
- ✓ Online status tracking is properly initialized
- ✓ All existing functionality preserved (no regressions)

### ❌ Failure Scenarios

#### Bug Condition Tests Fail
If bug condition tests fail, check:
1. **API Authentication**: Verify VPN_PANEL_USERNAME and VPN_PANEL_PASSWORD in .env
2. **API Endpoint**: Confirm VPN_PANEL_URL is correct and accessible
3. **x-ui API Enabled**: Check x-ui panel settings to ensure API is enabled
4. **Logs**: Review test output for API errors or fallback to direct DB

#### Preservation Tests Fail
If preservation tests fail, this indicates a regression:
1. Check subscription URL format changes
2. Verify mock mode still works
3. Review client data structure changes
4. Check VPN connectivity parameters

## Troubleshooting

### Database Access Errors
```
sqlite3.OperationalError: unable to open database file
```
**Solution**: Ensure x-ui is installed and database exists at `/etc/x-ui/x-ui.db`

### API Connection Errors
```
Cannot connect to host ... ssl:default [[SSL: WRONG_VERSION_NUMBER]]
```
**Solution**: 
- Check VPN_PANEL_URL uses correct protocol (http vs https)
- Verify x-ui panel is running: `systemctl status x-ui`
- Test panel access: `curl -k https://your-server-ip:port/login`

### Authentication Errors
```
Authentication failed: Invalid username or password
```
**Solution**: Verify credentials in .env match x-ui panel login

## Test Logs Location
Test logs are saved to:
- `tests/TASK_3_5_VERIFICATION_SUMMARY.md` - Bug condition test results
- `tests/TASK_3_6_VERIFICATION_SUMMARY.md` - Preservation test results

## Manual Verification (Alternative)

If automated tests cannot run, perform manual verification:

1. **Create Client via Bot**
   ```bash
   # Use bot to create a test client
   # Note the username
   ```

2. **Check x-ui Panel**
   - Login to x-ui web interface
   - Navigate to Inbounds → Clients
   - Find the test client
   - Verify it appears in the client list

3. **Simulate Traffic**
   - Connect to VPN using the client
   - Transfer some data (browse websites, download files)
   - Wait 1-2 minutes for statistics to update

4. **Verify Statistics**
   - Refresh x-ui panel
   - Check client statistics show:
     - Traffic usage > 0 GB
     - Online status when connected
     - Last connection time updated

5. **Check Database**
   ```bash
   sqlite3 /etc/x-ui/x-ui.db "SELECT email, up, down, enable FROM client_traffics WHERE email LIKE 'test_%';"
   ```
   - Verify entry exists for bot-created client
   - Confirm up/down values are > 0 after traffic

## Success Criteria

Task 4 is complete when:
- [ ] All 8 tests pass on the VPN server
- [ ] No errors or warnings in test output
- [ ] Bug condition tests confirm statistics tracking works
- [ ] Preservation tests confirm no regressions
- [ ] Manual verification (if needed) confirms statistics visible in x-ui panel

## Questions or Issues?

If you encounter any issues running the tests on the server, please provide:
1. Full test output (with -v flag)
2. Contents of .env file (redact sensitive values)
3. x-ui panel version: `x-ui version`
4. Python version: `python --version`
5. Any error messages from logs

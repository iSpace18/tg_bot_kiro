# Dual VPN Connectivity Fix - Bugfix Design

## Overview

This bugfix addresses the Reality configuration mismatch that prevents CDN bypass connections from working. The VPN service generates dual configurations (Direct + CDN Bypass) with different SNI values, but the Reality serverNames whitelist only includes Google domains. Adding "djanvpn.ru" to the serverNames array will enable the CDN bypass configuration to pass Reality validation, allowing users to connect through Cloudflare CDN for improved censorship circumvention.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when Reality serverNames array lacks "djanvpn.ru" while VPN URLs use sni=djanvpn.ru
- **Property (P)**: The desired behavior - both Direct and CDN bypass configurations should successfully validate and establish connections
- **Preservation**: Existing Direct VPN connections using www.google.com/google.com SNI must remain unchanged
- **Reality Protocol**: VLESS transport security layer that mimics TLS handshakes to legitimate domains
- **serverNames**: Reality configuration whitelist of allowed SNI (Server Name Indication) values
- **SNI (Server Name Indication)**: TLS extension that specifies the hostname the client is attempting to connect to
- **CDN Bypass**: Connection method routing traffic through Cloudflare CDN (djanvpn.ru) to circumvent IP-based blocks
- **Direct VPN**: Connection method using server IP directly with Google SNI for standard operation

## Bug Details

### Bug Condition

The bug manifests when the Reality configuration serverNames array contains only ["www.google.com", "google.com"] while the VPN service generates vless:// URLs with sni=djanvpn.ru for CDN bypass connections. The Reality protocol validates incoming connections by checking if the client's SNI matches any entry in the serverNames whitelist. When a client attempts to connect with sni=djanvpn.ru, Reality rejects the connection because "djanvpn.ru" is not in the whitelist.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type VLESSConnectionAttempt
  OUTPUT: boolean
  
  RETURN input.sni == "djanvpn.ru"
         AND "djanvpn.ru" NOT IN realityConfig.serverNames
         AND connectionValidationFails(input)
END FUNCTION
```

### Examples

- **CDN Bypass Connection Attempt**: Client tries to connect with `vless://uuid@djanvpn.ru:443?sni=djanvpn.ru` → Reality validation fails → Connection shows N/A ping status → User cannot establish VPN tunnel
- **Direct VPN Connection Attempt**: Client tries to connect with `vless://uuid@IP:443?sni=www.google.com` → Reality validation succeeds → Connection established → User has working VPN (this works correctly)
- **Dual Configuration Import**: User imports subscription with both configs → Only Direct VPN server appears as working → CDN Bypass server shows N/A or fails to connect
- **Edge Case - Manual SNI Override**: User manually changes SNI to "djanvpn.ru" in Direct config → Connection fails even though server IP is correct

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Direct VPN connections using sni=www.google.com must continue to work exactly as before
- Direct VPN connections using sni=google.com must continue to work exactly as before
- Reality validation for Google SNI values must remain unchanged
- All existing Reality parameters (privateKey, shortIds, dest, xver) must remain unchanged
- VPN service URL generation logic must remain unchanged (already generates correct dual configs)

**Scope:**
All inputs that do NOT involve sni=djanvpn.ru should be completely unaffected by this fix. This includes:
- Existing client connections using Google SNI values
- Reality handshake behavior for Google domains
- Traffic routing and protocol handling for established connections
- Client statistics tracking and traffic accounting

## Hypothesized Root Cause

Based on the bug description and code analysis, the root cause is clear:

1. **Incomplete serverNames Whitelist**: The Reality configuration in `config_reality.json` only includes Google domains in the serverNames array, but the VPN service generates URLs with "djanvpn.ru" SNI for CDN bypass
   - Current: `"serverNames": ["www.google.com", "google.com"]`
   - VPN service generates: `sni=djanvpn.ru` for CDN bypass config
   - Reality rejects connections when SNI doesn't match whitelist

2. **Configuration File Location**: The Reality configuration is stored in `config_reality.json` at the workspace root, which is read by xray-core at startup

3. **No Runtime Reload**: Changes to Reality configuration require xray process restart (SIGHUP signal) to take effect, which is already handled by the VPN service's `_restart_xray()` function

4. **VPN Service Already Correct**: The `bot/services/vpn_service.py` already generates correct dual configurations with appropriate SNI values - no code changes needed there

## Correctness Properties

Property 1: Bug Condition - CDN Bypass Connection Validation

_For any_ connection attempt where the client uses sni=djanvpn.ru AND "djanvpn.ru" is included in the Reality serverNames array, the Reality protocol SHALL successfully validate the connection, allowing the VPN tunnel to establish and showing proper connectivity status instead of N/A.

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Preservation - Direct VPN Connection Behavior

_For any_ connection attempt where the client uses sni=www.google.com OR sni=google.com (not sni=djanvpn.ru), the Reality protocol SHALL produce exactly the same validation behavior as before the fix, preserving all existing Direct VPN connection functionality.

**Validates: Requirements 3.1, 3.2, 3.3**

## Fix Implementation

### Changes Required

The fix requires a single configuration change to enable CDN bypass connections:

**File**: `config_reality.json`

**Location**: Line 48 (within the realitySettings object)

**Specific Changes**:
1. **Add djanvpn.ru to serverNames Array**: Modify the serverNames array to include "djanvpn.ru"
   - Current: `"serverNames": ["www.google.com", "google.com"]`
   - Fixed: `"serverNames": ["www.google.com", "google.com", "djanvpn.ru"]`
   - This allows Reality to accept connections with sni=djanvpn.ru

2. **Apply Configuration on Server**: After modifying config_reality.json, restart xray to load the new configuration
   - Method 1: Use existing VPN service restart mechanism (send SIGHUP to xray process)
   - Method 2: Manual restart via systemctl or docker-compose (if applicable)
   - Method 3: Run deployment script if available

3. **Verify No Other Changes Needed**: Confirm that no other Reality parameters require modification
   - privateKey: Keep existing value (MPnNzbMLF812adXAeJXYv3nY3M6gDWZJsc2kIlLAZnE)
   - shortIds: Keep existing values (["", "0123456789abcdef"])
   - dest: Keep existing value (www.google.com:443)
   - All other settings remain unchanged

4. **No Code Changes Required**: The VPN service already generates correct dual configurations
   - Direct config: `sni=www.google.com` (already works)
   - CDN bypass config: `sni=djanvpn.ru` (will work after serverNames fix)

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed configuration, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that CDN bypass connections fail with current configuration.

**Test Plan**: Attempt to establish VPN connections using both Direct and CDN bypass configurations with the UNFIXED config_reality.json. Observe that Direct connections succeed while CDN bypass connections fail validation.

**Test Cases**:
1. **CDN Bypass Connection Test**: Import subscription URL, attempt to connect to "⚡ | 🇳🇱 Netherlands Обход" server with sni=djanvpn.ru (will fail on unfixed config - shows N/A ping or connection timeout)
2. **Direct VPN Connection Test**: Import subscription URL, attempt to connect to "⚡ | 🇳🇱 Netherlands VPN" server with sni=www.google.com (will succeed on unfixed config - confirms existing functionality works)
3. **Manual SNI Test**: Manually create vless:// URL with server IP but sni=djanvpn.ru (will fail on unfixed config - confirms SNI validation is the issue)
4. **Subscription Import Test**: Import full subscription with both configs (will show only 1 working server on unfixed config instead of 2)

**Expected Counterexamples**:
- CDN bypass connections fail with "connection timeout" or "N/A" ping status
- Reality logs (if accessible) show SNI validation failures for djanvpn.ru
- Only Direct VPN configuration establishes successful connection
- Possible causes: serverNames whitelist missing djanvpn.ru, incorrect SNI in URLs (already ruled out by code review)

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds (sni=djanvpn.ru), the fixed configuration produces the expected behavior (successful connection).

**Pseudocode:**
```
FOR ALL connectionAttempt WHERE connectionAttempt.sni == "djanvpn.ru" DO
  result := realityValidation_fixed(connectionAttempt)
  ASSERT result.validationSuccess == true
  ASSERT result.connectionEstablished == true
  ASSERT result.pingStatus != "N/A"
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold (sni != djanvpn.ru), the fixed configuration produces the same result as the original configuration.

**Pseudocode:**
```
FOR ALL connectionAttempt WHERE connectionAttempt.sni IN ["www.google.com", "google.com"] DO
  ASSERT realityValidation_original(connectionAttempt) == realityValidation_fixed(connectionAttempt)
END FOR
```

**Testing Approach**: Manual testing is sufficient for this configuration change because:
- The input domain is small (only 3 SNI values: www.google.com, google.com, djanvpn.ru)
- The change is declarative (configuration array modification, not code logic)
- Property-based testing would require complex VPN client simulation infrastructure
- Manual verification with real VPN clients provides stronger guarantees for this use case

**Test Plan**: Test existing Direct VPN connections with UNFIXED config to establish baseline behavior, then verify identical behavior after applying the fix.

**Test Cases**:
1. **Direct VPN Preservation (www.google.com)**: Connect to Direct VPN with sni=www.google.com before fix, record connection time and ping. Apply fix, reconnect, verify identical behavior.
2. **Direct VPN Preservation (google.com)**: Connect to Direct VPN with manually modified sni=google.com before fix, verify it works. Apply fix, reconnect, verify identical behavior.
3. **Traffic Routing Preservation**: Establish Direct VPN connection, browse websites, verify traffic routing works. Apply fix, reconnect, verify identical traffic routing behavior.
4. **Statistics Tracking Preservation**: Check client traffic statistics before fix. Apply fix, use VPN, verify statistics continue to increment correctly.

### Unit Tests

- Test Reality configuration parsing (verify serverNames array is correctly read)
- Test SNI validation logic (verify djanvpn.ru is accepted after fix)
- Test configuration file syntax (verify JSON is valid after modification)

### Property-Based Tests

Not applicable for this bugfix - the change is a declarative configuration modification with a small, well-defined input domain (3 SNI values). Manual testing provides sufficient coverage.

### Integration Tests

- Test full VPN connection flow with CDN bypass configuration (import subscription → connect to CDN bypass server → verify tunnel established → browse websites → verify traffic routed correctly)
- Test dual configuration import (import subscription → verify 2 servers appear → connect to both → verify both show proper ping status)
- Test switching between Direct and CDN bypass (connect to Direct → disconnect → connect to CDN bypass → verify both work)
- Test that existing clients continue working after configuration change (apply fix → restart xray → verify existing connected clients remain connected or can reconnect)

## Deployment Steps

### 1. Backup Current Configuration
```bash
cp config_reality.json config_reality.json.backup
```

### 2. Modify Configuration File
Edit `config_reality.json` line 48:
```json
"serverNames": ["www.google.com", "google.com", "djanvpn.ru"]
```

### 3. Validate JSON Syntax
```bash
python3 -m json.tool config_reality.json > /dev/null && echo "Valid JSON" || echo "Invalid JSON"
```

### 4. Apply Configuration (Choose One Method)

**Method A - Using VPN Service Restart (Recommended)**:
```python
# The VPN service already has _restart_xray() function
# It will be called automatically after any client modification
# Or manually trigger via Python:
import os
import signal
for pid_str in os.listdir('/proc'):
    if pid_str.isdigit():
        try:
            with open(f'/proc/{pid_str}/cmdline', 'rb') as f:
                if b'xray-linux' in f.read():
                    os.kill(int(pid_str), signal.SIGHUP)
        except: pass
```

**Method B - Using Systemctl (If xray is a service)**:
```bash
systemctl restart xray
# or
systemctl reload xray
```

**Method C - Using Docker (If running in container)**:
```bash
docker-compose restart
# or
docker restart <container_name>
```

### 5. Verify Configuration Applied
```bash
# Check xray logs for successful reload
journalctl -u xray -n 50
# or
docker logs <container_name> --tail 50
```

### 6. Test Both Configurations
- Import subscription URL in VPN client
- Verify 2 servers appear: "⚡ | 🇳🇱 Netherlands VPN" and "⚡ | 🇳🇱 Netherlands Обход"
- Connect to Direct VPN → verify connection succeeds
- Connect to CDN Bypass → verify connection succeeds (this should now work)
- Check ping status for both → verify neither shows N/A

### 7. Monitor for Issues
- Check client connection logs for any validation errors
- Verify existing clients can still connect
- Monitor traffic statistics to ensure tracking still works

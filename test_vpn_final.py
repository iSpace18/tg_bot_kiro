#!/usr/bin/env python3
"""
Final VPN configuration test - verify single CDN bypass server works correctly.
"""

import subprocess
import sys

def test_domain_resolution():
    """Test that djanvpn.ru resolves through Cloudflare."""
    print("=" * 80)
    print("TEST 1: Domain Resolution")
    print("=" * 80)
    
    try:
        result = subprocess.run(
            ["nslookup", "djanvpn.ru"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if "188.114.9" in result.stdout:
            print("✅ PASS: djanvpn.ru resolves to Cloudflare CDN")
            print(f"   Output: {result.stdout.split('Address:')[-1].strip()}")
            return True
        else:
            print("❌ FAIL: Domain doesn't resolve to Cloudflare")
            print(f"   Output: {result.stdout}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_xray_listening():
    """Test that xray is listening on port 443."""
    print("\n" + "=" * 80)
    print("TEST 2: Xray Service")
    print("=" * 80)
    
    try:
        result = subprocess.run(
            ["ssh", "root@89.44.76.190", "ss -tlnp | grep :443"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if "xray" in result.stdout.lower():
            print("✅ PASS: Xray is listening on port 443")
            return True
        else:
            print("❌ FAIL: Xray not found on port 443")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_reality_config():
    """Test Reality configuration."""
    print("\n" + "=" * 80)
    print("TEST 3: Reality Configuration")
    print("=" * 80)
    
    try:
        result = subprocess.run(
            ["ssh", "root@89.44.76.190", 
             "cat /usr/local/x-ui/bin/config.json | python3 -m json.tool | grep -A2 serverNames"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if "djanvpn.ru" in result.stdout:
            print("✅ PASS: Reality serverNames includes djanvpn.ru")
            print(f"   Config: {result.stdout.strip()}")
            return True
        else:
            print("❌ FAIL: djanvpn.ru not in serverNames")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_bot_running():
    """Test that bot is running."""
    print("\n" + "=" * 80)
    print("TEST 4: Bot Status")
    print("=" * 80)
    
    try:
        result = subprocess.run(
            ["ssh", "root@89.44.76.190", "docker ps | grep vpn_telegram_bot"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if "Up" in result.stdout:
            print("✅ PASS: Bot container is running")
            return True
        else:
            print("❌ FAIL: Bot container not running")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    """Run all tests."""
    print("\n🔍 VPN Configuration Final Test")
    print("Testing single CDN bypass configuration with RKN circumvention\n")
    
    tests = [
        test_domain_resolution,
        test_xray_listening,
        test_reality_config,
        test_bot_running
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
        print("\nConfiguration is ready:")
        print("  • Server: djanvpn.ru:443")
        print("  • Protocol: VLESS + Reality")
        print("  • SNI: djanvpn.ru")
        print("  • CDN: Cloudflare")
        print("  • RKN Bypass: Enabled")
        print("\nYou can now request trial subscription in the bot!")
        return 0
    else:
        print(f"\n❌ {total - passed} TEST(S) FAILED")
        print("\nPlease fix the issues before using the VPN.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Check if sniffing is enabled in Xray config."""

import json

CONFIG_PATH = "/usr/local/x-ui/bin/config.json"

with open(CONFIG_PATH, 'r') as f:
    config = json.load(f)

# Find VLESS inbound on port 443
for inbound in config.get('inbounds', []):
    if inbound.get('port') == 443 and inbound.get('protocol') == 'vless':
        print(f"✅ Found VLESS inbound on port 443")
        print(f"Tag: {inbound.get('tag', 'N/A')}")
        print(f"Sniffing config:")
        print(json.dumps(inbound.get('sniffing'), indent=2))
        
        if inbound.get('sniffing', {}).get('enabled'):
            print("\n✅ Sniffing is ENABLED - statistics should work!")
        else:
            print("\n❌ Sniffing is DISABLED - statistics won't work!")
        break
else:
    print("❌ VLESS inbound on port 443 not found")

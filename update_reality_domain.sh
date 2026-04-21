#!/bin/bash

# Update Reality configuration to use djanvpn.ru domain

DOMAIN="djanvpn.ru"
XUI_DB="/etc/x-ui/x-ui.db"

echo "=========================================="
echo "Updating Reality configuration"
echo "New domain: $DOMAIN"
echo "=========================================="

# Backup current database
cp $XUI_DB ${XUI_DB}.backup_$(date +%Y%m%d_%H%M%S)
echo "✅ Database backed up"

# Update streamSettings in database
sqlite3 $XUI_DB <<EOF
UPDATE inbounds 
SET streamSettings = json_set(
    streamSettings,
    '$.realitySettings.dest', '$DOMAIN:443',
    '$.realitySettings.serverNames', json_array('$DOMAIN', 'www.$DOMAIN')
)
WHERE protocol = 'vless';
EOF

echo "✅ Reality configuration updated in database"

# Restart x-ui service
systemctl restart x-ui
echo "✅ x-ui service restarted"

# Show updated configuration
echo ""
echo "=========================================="
echo "Updated Reality settings:"
echo "=========================================="
sqlite3 $XUI_DB "SELECT json_extract(streamSettings, '$.realitySettings') FROM inbounds WHERE protocol='vless';" | python3 -m json.tool

echo ""
echo "=========================================="
echo "✅ Configuration update complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Update bot configuration (VPN_PANEL_URL and subscription URL generation)"
echo "2. Test VPN connection with new domain"

#!/bin/bash

# Restore script from Reality migration backup
# Created: 2026-04-20 21:48:57

BACKUP_DIR="/root/backup_before_reality_20260420_214857"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "Error: Backup directory not found: $BACKUP_DIR"
    exit 1
fi

echo "Restoring from backup: $BACKUP_DIR"

# Stop services
systemctl stop x-ui
systemctl stop vpn-bot

# Restore x-ui config
cp "$BACKUP_DIR/config.json" /usr/local/x-ui/bin/config.json
echo "Restored x-ui config"

# Restore bot
rm -rf /opt/vpn_bot
cp -r "$BACKUP_DIR/vpn_bot" /opt/vpn_bot
echo "Restored bot"

# Start services
systemctl start x-ui
systemctl start vpn-bot

echo "Services restarted"
echo ""
echo "Restoration complete!"
echo "Check status:"
echo "  systemctl status x-ui"
echo "  systemctl status vpn-bot"

#!/bin/bash
# Deployment script for VPN Bot

set -e

echo "🚀 Starting VPN Bot deployment..."

# Update system
echo "📦 Updating system packages..."
apt-get update
apt-get install -y python3 python3-pip python3-venv git

# Create bot directory
BOT_DIR="/opt/vpn_bot"
echo "📁 Creating bot directory: $BOT_DIR"
mkdir -p $BOT_DIR

# Copy files to server (this script assumes files are already on server)
echo "📋 Copying bot files..."
cp -r . $BOT_DIR/
cd $BOT_DIR

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📚 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create systemd service
echo "⚙️ Creating systemd service..."
cat > /etc/systemd/system/vpn-bot.service << 'EOF'
[Unit]
Description=VPN Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/vpn_bot
Environment="PYTHONPATH=/opt/vpn_bot"
ExecStart=/opt/vpn_bot/venv/bin/python bot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
echo "🔄 Enabling and starting service..."
systemctl daemon-reload
systemctl enable vpn-bot.service
systemctl restart vpn-bot.service

echo "✅ Deployment complete!"
echo ""
echo "📊 Service status:"
systemctl status vpn-bot.service --no-pager
echo ""
echo "📝 Useful commands:"
echo "  - View logs: journalctl -u vpn-bot.service -f"
echo "  - Restart bot: systemctl restart vpn-bot.service"
echo "  - Stop bot: systemctl stop vpn-bot.service"
echo "  - Check status: systemctl status vpn-bot.service"

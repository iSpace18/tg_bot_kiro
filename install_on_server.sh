#!/bin/bash
# One-command installation script
# Run on server: curl -sSL https://your-url/install.sh | bash
# Or manually: bash install_on_server.sh

set -e

echo "🚀 VPN Bot Installation Script"
echo "================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root"
    exit 1
fi

BOT_DIR="/opt/vpn_bot"

# Install dependencies
echo "📦 Installing dependencies..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv unzip sqlite3 > /dev/null 2>&1

# Navigate to bot directory
cd $BOT_DIR

# Check if files exist
if [ ! -f "vpn_bot.zip" ]; then
    echo "❌ vpn_bot.zip not found in $BOT_DIR"
    echo "Please upload vpn_bot.zip first using:"
    echo "  scp vpn_bot.zip root@89.44.76.190:/opt/vpn_bot/"
    exit 1
fi

# Unzip files
echo "📂 Extracting files..."
unzip -o vpn_bot.zip > /dev/null 2>&1

# Create virtual environment
echo "🐍 Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo "📚 Installing Python packages..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1

# Create data directory
mkdir -p data

# Check x-ui database
if [ ! -f "/etc/x-ui/x-ui.db" ]; then
    echo "⚠️  Warning: /etc/x-ui/x-ui.db not found"
    echo "Make sure 3x-ui is installed"
fi

# Create systemd service
echo "⚙️  Creating systemd service..."
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
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
echo "🔄 Starting service..."
systemctl daemon-reload
systemctl enable vpn-bot.service
systemctl restart vpn-bot.service

# Wait a bit for service to start
sleep 3

# Show status
echo ""
echo "✅ Installation complete!"
echo ""
echo "📊 Service Status:"
systemctl status vpn-bot.service --no-pager -l
echo ""
echo "📝 Useful commands:"
echo "  View logs:    journalctl -u vpn-bot.service -f"
echo "  Restart bot:  systemctl restart vpn-bot.service"
echo "  Stop bot:     systemctl stop vpn-bot.service"
echo "  Check status: systemctl status vpn-bot.service"

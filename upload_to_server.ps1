# PowerShell script to upload bot files to server

$SERVER = "89.44.76.190"
$USER = "root"
$REMOTE_PATH = "/opt/vpn_bot"

Write-Host "🚀 Uploading VPN Bot to server..." -ForegroundColor Green

# Create remote directory
Write-Host "📁 Creating remote directory..." -ForegroundColor Yellow
ssh ${USER}@${SERVER} "mkdir -p ${REMOTE_PATH}"

# Upload files using SCP
Write-Host "📤 Uploading files..." -ForegroundColor Yellow

# Upload bot directory
scp -r bot ${USER}@${SERVER}:${REMOTE_PATH}/

# Upload other files
scp .env ${USER}@${SERVER}:${REMOTE_PATH}/
scp requirements.txt ${USER}@${SERVER}:${REMOTE_PATH}/
scp deploy.sh ${USER}@${SERVER}:${REMOTE_PATH}/
scp setup_reality.py ${USER}@${SERVER}:${REMOTE_PATH}/
scp docker-compose.yml ${USER}@${SERVER}:${REMOTE_PATH}/
scp Dockerfile ${USER}@${SERVER}:${REMOTE_PATH}/
scp README.md ${USER}@${SERVER}:${REMOTE_PATH}/

Write-Host "✅ Files uploaded successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Cyan
Write-Host "1. Connect to server: ssh ${USER}@${SERVER}"
Write-Host "2. Go to bot directory: cd ${REMOTE_PATH}"
Write-Host "3. Run deployment: chmod +x deploy.sh && ./deploy.sh"
Write-Host ""
Write-Host "Or run deployment directly:" -ForegroundColor Yellow
Write-Host "ssh ${USER}@${SERVER} 'cd ${REMOTE_PATH} && chmod +x deploy.sh && ./deploy.sh'"

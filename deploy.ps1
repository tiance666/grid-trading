# 设置变量
$SERVER_IP = "47.113.144.26"
$SERVER_USER = "root"
$SERVER_PASSWORD = "Chc20090629"
$GITHUB_USERNAME = "tiance666"
$REPO_NAME = "grid-trading"

# 生成部署命令
$DEPLOY_COMMANDS = @"
cd /home/trading/grid-trading
rm -rf *
git clone https://github.com/$GITHUB_USERNAME/$REPO_NAME.git .
pip3 install -r requirements.txt
cat > /etc/supervisor/conf.d/grid-trading.conf << 'EOL'
[program:grid-trading]
directory=/home/trading/grid-trading
command=python3 -m uvicorn app:app --host 0.0.0.0 --port 8000
autostart=true
autorestart=true
stderr_logfile=/var/log/grid-trading.err.log
stdout_logfile=/var/log/grid-trading.out.log
environment=PYTHONPATH="/home/trading/grid-trading"
user=root
EOL
systemctl restart supervisor
supervisorctl reread
supervisorctl update
supervisorctl status grid-trading
"@

# 安装必要的PowerShell模块
Write-Host "Installing required PowerShell modules..."
Install-Module -Name Posh-SSH -Force -AllowClobber

# 连接到服务器并执行命令
Write-Host "Connecting to server..."
$secpasswd = ConvertTo-SecureString $SERVER_PASSWORD -AsPlainText -Force
$creds = New-Object System.Management.Automation.PSCredential ($SERVER_USER, $secpasswd)
$session = New-SSHSession -ComputerName $SERVER_IP -Credential $creds -Force

if ($session) {
    Write-Host "Connection successful, starting deployment..."
    $result = Invoke-SSHCommand -SessionId $session.SessionId -Command $DEPLOY_COMMANDS
    Write-Host "Deployment results:"
    Write-Host $result.Output
    
    Remove-SSHSession -SessionId $session.SessionId
    Write-Host "Deployment completed!"
} else {
    Write-Host "Connection failed. Please check server configuration and network connection."
} 
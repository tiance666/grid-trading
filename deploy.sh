#!/bin/bash

# 后端部署步骤
echo "开始部署后端..."
cd /home/trading/grid-trading

# 清理旧文件
rm -rf *

# 克隆代码
git clone https://github.com/tiance666/grid-trading.git .

# 安装依赖
pip3 install -r requirements.txt

# 配置supervisor
cat > /etc/supervisor/conf.d/grid-trading.conf << EOL
[program:grid-trading]
directory=/home/trading/grid-trading
command=/usr/bin/python3 -m uvicorn src.server.app:app --host 0.0.0.0 --port 8000
autostart=true
autorestart=true
stderr_logfile=/var/log/grid-trading.err.log
stdout_logfile=/var/log/grid-trading.out.log
environment=PYTHONPATH="/home/trading/grid-trading"
user=root
EOL

# 重启supervisor
systemctl restart supervisor
supervisorctl reread
supervisorctl update
supervisorctl status grid-trading

echo "后端部署完成！" 
import paramiko

def fix_static():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect('47.113.144.26', username='root', password='Chc20090629')
        
        # 检查dist目录
        stdin, stdout, stderr = ssh.exec_command('ls -la /home/trading/grid-trading/src/server/dist/')
        print("dist目录内容:")
        print(stdout.read().decode())
        
        # 确保dist目录存在
        stdin, stdout, stderr = ssh.exec_command('mkdir -p /home/trading/grid-trading/src/server/dist/')
        
        # 复制index.html到dist目录
        stdin, stdout, stderr = ssh.exec_command('cp /home/trading/grid-trading/src/server/dist/index.html /home/trading/grid-trading/src/server/dist/')
        
        # 修改app.py中的静态文件配置
        config = """import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.append(str(project_root))
sys.path.append(str(current_dir.parent))  # 添加src目录

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from typing import Dict, List
import json
import asyncio
import logging
import argparse

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

from trading.grid_trading import GridTradingStrategy
from exchange.binance_api import BinanceAPI

app = FastAPI()

# 挂载静态文件目录
static_dir = current_dir / "dist"
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

# 存储API配置和WebSocket连接
api_config = {}
trading_bot = None"""
        
        stdin, stdout, stderr = ssh.exec_command('cat > /home/trading/grid-trading/src/server/app.py', get_pty=True)
        stdin.write(config)
        stdin.close()
        
        print("\n更新app.py完成")
        
        # 重启服务
        stdin, stdout, stderr = ssh.exec_command('supervisorctl restart grid-trading')
        print("\n重启服务:")
        print(stdout.read().decode())
        
        # 检查状态
        stdin, stdout, stderr = ssh.exec_command('supervisorctl status')
        print("\n服务状态:")
        print(stdout.read().decode())
        
    except Exception as e:
        print(f"错误: {str(e)}")
    finally:
        ssh.close()

if __name__ == '__main__':
    fix_static() 
#!/bin/bash

# 设置环境变量
export BINANCE_API_KEY="CQ9gOQKW98k8ZXN080Jx9i4GRpiulh5cKGBivt7NwXWeqrTsgqmj4nbPj8ClQcfa"
export BINANCE_API_SECRET="lr2BCHjJwO1eP0hhHrPXnfnHW8cBDaq9gSQ3qOwgmRvfzT45DauRAbLL04Qf615l"

# 安装所需的包
pip install fastapi uvicorn python-binance pandas ta

# 启动服务器
python src/server/app.py --host 0.0.0.0 

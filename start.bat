@echo off
echo 正在检查 Python 环境...
python --version 2>nul
if errorlevel 1 (
    echo 未检测到 Python，请先安装 Python 3.7 或更高版本
    pause
    exit
)

echo 正在安装 Python 依赖...
pip install -r requirements.txt

echo 正在启动应用...
npm start

pause 
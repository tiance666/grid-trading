@echo off
pip install fastapi uvicorn python-binance pandas ta
python src\server\app.py --host 0.0.0.0 
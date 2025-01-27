import paramiko

def update_app():
    # 创建SSH客户端
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # 连接到服务器
        ssh.connect('47.113.144.26', username='root', password='Chc20090629')
        
        # 创建新的app.py内容
        new_content = '''import logging
import asyncio
import argparse
from pathlib import Path
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from src.trading.binance_api import BinanceAPI
from src.trading.grid_trading import GridTradingStrategy

# Initialize FastAPI app
app = FastAPI()

# Get current directory
current_dir = Path(__file__).parent

# Global variables
api_config = None
trading_bot = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.last_prices = {"BTCUSDT": 0, "ETHUSDT": 0}
        self.kline_data = {"BTCUSDT": [], "ETHUSDT": []}
        self.current_interval = "1m"

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info(f"New WebSocket connection established, current connections: {len(self.active_connections)}")
        if self.kline_data["BTCUSDT"]:
            await self.send_kline_data(websocket)
        await self.send_price_update(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logging.info(f"WebSocket connection closed, current connections: {len(self.active_connections)}")

    async def send_kline_data(self, websocket: WebSocket):
        try:
            await websocket.send_json({
                "type": "kline",
                "data": self.kline_data
            })
        except Exception as e:
            logging.error(f"Failed to send kline data: {str(e)}")

    async def broadcast_kline_data(self):
        for connection in self.active_connections:
            try:
                await self.send_kline_data(connection)
            except Exception as e:
                logging.error(f"Failed to broadcast kline data: {str(e)}")
                await self.disconnect(connection)

    async def update_kline_data(self, symbol: str, interval: str, data: list):
        self.kline_data[symbol] = data
        self.current_interval = interval
        await self.broadcast_kline_data()

    async def send_price_update(self, websocket: WebSocket):
        try:
            await websocket.send_json({
                "type": "price_update",
                "data": self.last_prices
            })
        except Exception as e:
            logging.error(f"Failed to send price update: {str(e)}")

    async def broadcast_price_update(self):
        for connection in self.active_connections:
            try:
                await self.send_price_update(connection)
            except Exception as e:
                logging.error(f"Failed to broadcast price update: {str(e)}")
                await self.disconnect(connection)

    async def update_prices(self, symbol: str, price: float):
        self.last_prices[symbol] = price
        await self.broadcast_price_update()

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "interval_change":
                interval = data.get("interval", "1m")
                await update_kline_data_for_all_symbols(interval)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logging.error(f"WebSocket error: {str(e)}")
        manager.disconnect(websocket)

async def update_kline_data_for_all_symbols(interval: str):
    try:
        if not api_config:
            return

        exchange = BinanceAPI(api_config["api_key"], api_config["api_secret"])
        symbols = ["BTCUSDT", "ETHUSDT"]

        for symbol in symbols:
            klines = await exchange.get_klines(symbol, interval)
            formatted_data = []
            for k in klines:
                formatted_data.append({
                    'time': k[0] / 1000,
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5])
                })
            await manager.update_kline_data(symbol, interval, formatted_data)

    except Exception as e:
        logging.error(f"Error updating kline data: {str(e)}")

async def kline_update_task():
    while True:
        try:
            if api_config and manager.active_connections:
                await update_kline_data_for_all_symbols(manager.current_interval)
            else:
                if not api_config:
                    logging.info("Waiting for API configuration...")
                if not manager.active_connections:
                    logging.info("Waiting for WebSocket connections...")
        except Exception as e:
            logging.error(f"Error in kline update task: {str(e)}")

        await asyncio.sleep(10)

async def price_update_task():
    while True:
        try:
            if api_config and manager.active_connections:
                exchange = BinanceAPI(api_config["api_key"], api_config["api_secret"])
                for symbol in ["BTCUSDT", "ETHUSDT"]:
                    price = await exchange.get_price(symbol)
                    await manager.update_prices(symbol, price)
            else:
                if not api_config:
                    logging.info("Waiting for API configuration...")
                if not manager.active_connections:
                    logging.info("Waiting for WebSocket connections...")
        except Exception as e:
            logging.error(f"Error in price update task: {str(e)}")

        await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(kline_update_task())
    asyncio.create_task(price_update_task())

class APIConfig(BaseModel):
    api_key: str
    api_secret: str

@app.get("/api/klines")
async def get_kline_data(symbol: str, interval: str):
    try:
        if not api_config:
            raise HTTPException(status_code=400, detail="Please configure API keys first")

        exchange = BinanceAPI(api_config["api_key"], api_config["api_secret"])
        klines = await exchange.get_klines(symbol, interval)

        formatted_data = []
        for k in klines:
            formatted_data.append({
                'time': k[0] / 1000,
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4])
            })

        return formatted_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/preview_grids")
async def preview_grids(symbol: str, grid_count: int, grid_height: float, investment: float = None):
    try:
        if not api_config:
            raise HTTPException(status_code=400, detail="Please configure API keys first")

        exchange = BinanceAPI(api_config["api_key"], api_config["api_secret"])
        current_price = await exchange.get_price(symbol)

        price_range = current_price * (grid_height / 100)
        grid_interval = price_range / grid_count

        grid_prices = []
        for i in range(grid_count + 1):
            price = current_price - (price_range / 2) + (i * grid_interval)
            if symbol == "BTCUSDT":
                price = round(price, 1)
            elif symbol == "ETHUSDT":
                price = round(price, 2)

            usdt_amount = None
            if investment:
                per_grid_investment = investment / grid_count
                usdt_amount = round(per_grid_investment, 2)

            grid_prices.append({
                "index": i + 1,
                "price": price,
                "type": "Buy" if i == 0 else "Sell" if i == grid_count else "Both",
                "usdt_amount": usdt_amount
            })

        return grid_prices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return FileResponse(str(current_dir / "dist" / "index.html"))

@app.post("/api/save_config")
async def save_api_config(config: APIConfig):
    global api_config
    try:
        api_config = config.dict()
        return {"status": "success", "message": "API configuration saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/start_trading")
async def start_grid_trading(config: dict):
    global trading_bot
    try:
        if not api_config:
            return {"status": "error", "message": "Please configure API keys first"}

        if trading_bot:
            return {"status": "error", "message": "Trading is already running"}

        exchange = BinanceAPI(api_config["api_key"], api_config["api_secret"])

        is_futures = config.get('tradeType') == 'futures'
        leverage = config.get('leverage', 1) if is_futures else 1

        trading_bot = GridTradingStrategy(
            exchange_api=exchange,
            symbol=config['symbol'],
            grid_height=config['gridHeight'],
            total_grids=config['gridCount'],
            investment=config['investment'],
            per_grid_amount=config.get('perGridAmount'),
            is_futures=is_futures,
            leverage=leverage
        )

        await trading_bot.start()
        return {"status": "success", "message": "Trading started successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/stop_trading")
async def stop_grid_trading():
    global trading_bot
    try:
        if not trading_bot:
            return {"status": "error", "message": "No active trading"}

        await trading_bot.stop()
        trading_bot = None
        return {"status": "success", "message": "Trading stopped successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    from fastapi.middleware.cors import CORSMiddleware

    origins = [
        "http://localhost",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
        "http://tiance.kesug.com",
        "https://tiance.kesug.com",
        "https://tiance666.github.io",
        "*"
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    uvicorn.run(app, host=args.host, port=args.port)
'''
        
        # 写入新的app.py文件
        stdin, stdout, stderr = ssh.exec_command(f'echo "{new_content}" > /home/trading/grid-trading/src/server/app.py')
        
        # 重启服务
        stdin, stdout, stderr = ssh.exec_command('supervisorctl restart grid-trading')
        print("重启服务:")
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
    update_app() 
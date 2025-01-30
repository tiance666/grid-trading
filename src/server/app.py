import sys
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
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from typing import Dict, List, Optional
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

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源访问，包括GitHub Pages
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录
current_dir = os.path.dirname(os.path.abspath(__file__))
dist_dir = os.path.join(current_dir, "dist")

# 存储API配置和WebSocket连接
api_config = {}
trading_bot = None

# 创建公共API实例用于查询价格
public_api = BinanceAPI(None, None)

# WebSocket连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.last_prices = {"BTCUSDT": None, "ETHUSDT": None}
        self.kline_data = {"BTCUSDT": [], "ETHUSDT": []}
        self.current_interval = "1m"

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info(f"新的WebSocket连接建立，当前连接数: {len(self.active_connections)}")
        
        # 如果有最新价格，立即发送
        if any(price is not None for price in self.last_prices.values()):
            await self.send_price_update(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logging.info(f"WebSocket连接断开，当前连接数: {len(self.active_connections)}")

    async def send_price_update(self, websocket: WebSocket):
        try:
            for symbol, price in self.last_prices.items():
                if price is not None:
                    await websocket.send_json({
                        "type": "price",
                        "symbol": symbol,
                        "price": price
                    })
        except Exception as e:
            logging.error(f"发送价格更新失败: {str(e)}")

    async def broadcast_price_update(self):
        for connection in self.active_connections:
            try:
                await self.send_price_update(connection)
            except Exception as e:
                logging.error(f"广播价格更新失败: {str(e)}")
                await self.disconnect(connection)

    async def update_prices(self, symbol: str, price: float):
        self.last_prices[symbol] = price
        await self.broadcast_price_update()

manager = ConnectionManager()

# WebSocket连接端点
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logging.error(f"WebSocket错误: {str(e)}")
        manager.disconnect(websocket)

# 价格更新任务
async def price_update_task():
    while True:
        try:
            if manager.active_connections:
                # 使用公共API获取价格
                for symbol in ["BTCUSDT", "ETHUSDT"]:
                    try:
                        price = await public_api.get_price(symbol)
                        if price and price > 0:
                            await manager.update_prices(symbol, price)
                    except Exception as e:
                        logging.error(f"获取{symbol}价格失败: {str(e)}")
        except Exception as e:
            logging.error(f"价格更新错误: {str(e)}")
        
        await asyncio.sleep(1)

# 启动时运行所有任务
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(price_update_task())

class APIConfig(BaseModel):
    api_key: str
    api_secret: str

@app.get("/")
async def root():
    current_dir = Path(__file__).parent
    index_path = current_dir / "dist" / "index.html"
    return FileResponse(str(index_path))

@app.post("/api/save_config")
async def save_api_config(config: APIConfig):
    """保存API配置"""
    global api_config
    try:
        # 验证API密钥
        exchange = BinanceAPI(config.api_key, config.api_secret)
        # 测试API连接
        await exchange.get_price("BTCUSDT")
        
        # 保存配置
        api_config = config.dict()
        logging.info("API配置已保存并验证成功")
        return {"status": "success", "message": "API配置已保存并验证成功"}
        
    except Exception as e:
        logging.error(f"API配置保存失败: {str(e)}")
        raise HTTPException(status_code=400, detail=f"API配置无效: {str(e)}")

# 添加K线数据获取端点
@app.get("/api/klines")
async def get_klines(symbol: str, interval: str = "1m", limit: int = 100, start_time: str = None, end_time: str = None):
    """获取K线数据
    
    Args:
        symbol: 交易对
        interval: K线间隔，支持 1m, 3m, 5m, 15m, 30m, 1h, 4h, 1d
        limit: 获取的K线数量，默认100
        start_time: 开始时间，格式如 "2023-01-01"
        end_time: 结束时间，格式如 "2024-01-01"
    """
    try:
        # 验证时间间隔
        valid_intervals = ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"]
        if interval not in valid_intervals:
            raise ValueError(f"无效的时间间隔，支持的间隔: {', '.join(valid_intervals)}")
            
        # 如果提供了时间范围，使用历史K线接口
        if start_time:
            klines = await public_api.get_historical_klines(
                symbol=symbol,
                interval=interval,
                start_str=start_time,
                end_str=end_time
            )
        else:
            # 否则使用普通K线接口
            klines = await public_api.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
        
        # 转换数据格式以适应图表库
        formatted_klines = []
        for k in klines:
            formatted_klines.append({
                "time": k[0] // 1000,  # 转换为秒级时间戳
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4])
            })
            
        return formatted_klines
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"获取K线数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取K线数据失败: {str(e)}")

# 添加GridConfig模型类
class GridConfig(BaseModel):
    """网格配置模型"""
    symbol: str
    grid_count: int
    grid_height: float
    investment: Optional[float] = None  # 可选参数，总投资金额
    per_grid_amount: Optional[float] = None  # 可选参数，每格交易数量
    trade_type: str  # 'spot' 或 'futures'
    leverage: Optional[int] = None  # 杠杆倍数，仅在 trade_type 为 'futures' 时使用

@app.post("/api/preview")
async def preview_grid(grid_config: GridConfig):
    """预览网格价格"""
    try:
        # 验证参数
        if grid_config.grid_count < 4 or grid_config.grid_count > 50:
            raise ValueError("网格数量必须在4-50之间")
            
        if grid_config.grid_height < 0.1 or grid_config.grid_height > 10:
            raise ValueError("网格高度必须在0.1%-10%之间")
            
        # 验证交易类型
        if grid_config.trade_type not in ['spot', 'futures']:
            raise ValueError("交易类型必须是'spot'或'futures'")
            
        # 验证杠杆倍数
        if grid_config.trade_type == 'futures':
            if grid_config.leverage is None:
                raise ValueError("合约交易必须设置杠杆倍数")
            if not isinstance(grid_config.leverage, int) or grid_config.leverage < 1 or grid_config.leverage > 125:
                raise ValueError("杠杆倍数必须在1-125之间")
        
        # 验证投资金额或每格数量
        if grid_config.investment is None and grid_config.per_grid_amount is None:
            raise ValueError("必须设置总投资金额或每格交易数量")
            
        # 获取当前价格
        try:
            current_price = await public_api.get_price(grid_config.symbol)
            if not current_price or current_price <= 0:
                raise ValueError("无法获取有效的当前价格")
        except Exception as e:
            logging.error(f"获取{grid_config.symbol}价格失败: {str(e)}")
            raise ValueError(f"获取当前价格失败: {str(e)}")
        
        # 计算网格价格
        price_range = current_price * (grid_config.grid_height / 100)
        upper_price = current_price + (price_range / 2)
        lower_price = current_price - (price_range / 2)
        grid_interval = (upper_price - lower_price) / grid_config.grid_count
        
        grid_prices = []
        grid_types = []
        
        for i in range(grid_config.grid_count + 1):
            price = lower_price + (i * grid_interval)
            # 根据不同交易对调整价格精度
            if grid_config.symbol == "BTCUSDT":
                price = round(price, 1)
            elif grid_config.symbol == "ETHUSDT":
                price = round(price, 2)
                
            grid_prices.append(price)
            # 当前价格附近的网格设为双向
            price_diff_percent = abs(price - current_price) / current_price * 100
            if price_diff_percent < 0.1:  # 价差小于0.1%视为当前价格
                grid_types.append("current")
            else:
                grid_types.append("buy" if price < current_price else "sell")
                
        # 计算每格投资金额或数量
        if grid_config.per_grid_amount:
            quantity_per_grid = grid_config.per_grid_amount
            investment_per_grid = quantity_per_grid * current_price
            if grid_config.trade_type == 'futures':
                # 合约交易下,实际投资金额需要除以杠杆倍数
                investment_per_grid = investment_per_grid / grid_config.leverage
        else:
            investment_per_grid = grid_config.investment / grid_config.grid_count
            if grid_config.trade_type == 'futures':
                # 合约交易下,实际投资金额需要除以杠杆倍数
                actual_investment = investment_per_grid / grid_config.leverage
                quantity_per_grid = actual_investment / current_price
            else:
                quantity_per_grid = investment_per_grid / current_price
                
            # 根据不同交易对调整数量精度
            if grid_config.symbol == "BTCUSDT":
                quantity_per_grid = round(quantity_per_grid, 3)  # 0.001
            elif grid_config.symbol == "ETHUSDT":
                quantity_per_grid = round(quantity_per_grid, 2)  # 0.01
                
        return {
            "status": "success",
            "data": {
                "grid_prices": grid_prices,
                "grid_types": grid_types,
                "current_price": current_price,
                "quantity_per_grid": quantity_per_grid,
                "investment_per_grid": round(investment_per_grid, 2),
                "actual_investment_per_grid": round(investment_per_grid / grid_config.leverage if grid_config.trade_type == 'futures' else investment_per_grid, 2),
                "trade_type": grid_config.trade_type,
                "leverage": grid_config.leverage if grid_config.trade_type == 'futures' else None
            }
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"生成网格预览失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成网格预览失败: {str(e)}")

@app.post("/api/start")
async def start_trading(config: dict):
    """启动网格交易"""
    global trading_bot
    
    try:
        if not api_config:
            raise HTTPException(status_code=400, detail="请先配置API密钥")
            
        if trading_bot and trading_bot.is_running:
            raise HTTPException(status_code=400, detail="交易已在运行中")
            
        # 验证参数
        required_fields = ["symbol", "grid_count", "grid_height", "trade_type"]
        if not all(field in config for field in required_fields):
            raise ValueError("缺少必要的交易参数")
            
        if config["grid_count"] < 4 or config["grid_count"] > 50:
            raise ValueError("网格数量必须在4-50之间")
            
        if config["grid_height"] < 0.1 or config["grid_height"] > 10:
            raise ValueError("网格高度必须在0.1%-10%之间")
            
        # 验证合约交易参数
        if config["trade_type"] == "futures":
            if "leverage" not in config or not isinstance(config["leverage"], int):
                raise ValueError("合约交易必须设置有效的杠杆倍数")
            if config["leverage"] < 1 or config["leverage"] > 125:
                raise ValueError("杠杆倍数必须在1-125之间")
            
        # 创建交易实例
        api = BinanceAPI(api_config["api_key"], api_config["api_secret"])
        trading_bot = GridTradingStrategy(
            exchange_api=api,
            symbol=config["symbol"],
            grid_height=config["grid_height"],
            total_grids=config["grid_count"],
            investment=config.get("investment"),
            per_grid_amount=config.get("per_grid_amount"),
            is_futures=(config["trade_type"] == "futures"),
            leverage=config.get("leverage", 1)
        )
        
        # 启动交易
        await trading_bot.start()
        
        return {
            "status": "success",
            "message": "交易已启动",
            "data": {
                "symbol": config["symbol"],
                "grid_count": config["grid_count"],
                "grid_height": config["grid_height"],
                "investment": config.get("investment"),
                "per_grid_amount": config.get("per_grid_amount"),
                "trade_type": config["trade_type"],
                "leverage": config.get("leverage")
            }
        }
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"启动交易失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stop")
async def stop_trading():
    """停止网格交易"""
    global trading_bot
    
    try:
        if not trading_bot or not trading_bot.is_running:
            raise HTTPException(status_code=400, detail="没有正在运行的交易")
            
        await trading_bot.stop()
        
        return {
            "status": "success",
            "message": "交易已停止"
        }
        
    except Exception as e:
        logging.error(f"停止交易失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 静态文件路由放在最后
app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
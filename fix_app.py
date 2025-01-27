import paramiko

def fix_app():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect('47.113.144.26', username='root', password='Chc20090629')
        
        # 获取原始app.py内容
        stdin, stdout, stderr = ssh.exec_command('cat /home/trading/grid-trading/src/server/app.py')
        original_content = stdout.read().decode()
        
        # 添加缺失的代码
        config = original_content + """

# WebSocket连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.last_prices = {"BTCUSDT": 0, "ETHUSDT": 0}
        self.kline_data = {"BTCUSDT": [], "ETHUSDT": []}
        self.current_interval = "1m"  # 默认时间间隔

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info(f"新的WebSocket连接建立，当前连接数: {len(self.active_connections)}")
        # 立即发送最新数据
        if self.kline_data["BTCUSDT"]:
            await self.send_kline_data(websocket)
        await self.send_price_update(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logging.info(f"WebSocket连接断开，当前连接数: {len(self.active_connections)}")

    async def send_kline_data(self, websocket: WebSocket):
        try:
            await websocket.send_json({
                "type": "kline",
                "data": self.kline_data
            })
        except Exception as e:
            logging.error(f"发送K线数据失败: {str(e)}")

    async def broadcast_kline_data(self):
        for connection in self.active_connections:
            try:
                await self.send_kline_data(connection)
            except Exception as e:
                logging.error(f"广播K线数据失败: {str(e)}")
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
            if data.get("type") == "interval_change":
                # 处理时间间隔变更
                interval = data.get("interval", "1m")
                await update_kline_data_for_all_symbols(interval)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logging.error(f"WebSocket错误: {str(e)}")
        manager.disconnect(websocket)

async def update_kline_data_for_all_symbols(interval: str):
    """更新所有交易对的K线数据"""
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
                    'time': k[0] / 1000,  # 转换为秒
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5])  # 添加成交量数据
                })
            await manager.update_kline_data(symbol, interval, formatted_data)

    except Exception as e:
        logging.error(f"更新K线数据错误: {str(e)}")

# K线数据更新任务
async def kline_update_task():
    while True:
        try:
            if api_config and manager.active_connections:
                await update_kline_data_for_all_symbols(manager.current_interval)
            else:
                if not api_config:
                    logging.info("等待API配置...")
                if not manager.active_connections:
                    logging.info("等待WebSocket连接...")
        except Exception as e:
            logging.error(f"K线数据更新错误: {str(e)}")

        await asyncio.sleep(10)  # 每10秒更新一次K线数据

# 价格更新任务
async def price_update_task():
    while True:
        try:
            if api_config and manager.active_connections:
                exchange = BinanceAPI(api_config["api_key"], api_config["api_secret"])
                # 获取BTC和ETH的价格
                for symbol in ["BTCUSDT", "ETHUSDT"]:
                    price = await exchange.get_price(symbol)
                    await manager.update_prices(symbol, price)
            else:
                if not api_config:
                    logging.info("等待API配置...")
                if not manager.active_connections:
                    logging.info("等待WebSocket连接...")
        except Exception as e:
            logging.error(f"价格更新错误: {str(e)}")

        await asyncio.sleep(1)  # 每秒更新一次价格

# 启动时运行所有任务
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
            raise HTTPException(status_code=400, detail="请先配置API密钥")

        exchange = BinanceAPI(api_config["api_key"], api_config["api_secret"])
        klines = await exchange.get_klines(symbol, interval)

        # 转换数据格式为TradingView图表库所需的格式
        formatted_data = []
        for k in klines:
            formatted_data.append({
                'time': k[0] / 1000,  # 转换为秒
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
    """预览网格价格"""
    try:
        if not api_config:
            raise HTTPException(status_code=400, detail="请先配置API密钥")

        exchange = BinanceAPI(api_config["api_key"], api_config["api_secret"])
        current_price = await exchange.get_price(symbol)

        # 计算网格价格
        price_range = current_price * (grid_height / 100)
        grid_interval = price_range / grid_count

        grid_prices = []
        for i in range(grid_count + 1):
            price = current_price - (price_range / 2) + (i * grid_interval)
            # 根据不同交易对调整价格精度
            if symbol == "BTCUSDT":
                price = round(price, 1)  # BTC价格精度为0.1
            elif symbol == "ETHUSDT":
                price = round(price, 2)  # ETH价格精度为0.01

            # 计算每格需要的USDT数量
            usdt_amount = None
            if investment:
                per_grid_investment = investment / grid_count
                usdt_amount = round(per_grid_investment, 2)

            grid_prices.append({
                "index": i + 1,
                "price": price,
                "type": "买入" if i == 0 else "卖出" if i == grid_count else "双向",
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
        return {"status": "success", "message": "API配置已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/start_trading")
async def start_grid_trading(config: dict):
    global trading_bot
    try:
        if not api_config:
            return {"status": "error", "message": "请先配置API密钥"}

        if trading_bot:
            return {"status": "error", "message": "交易已在运行"}

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
        return {"status": "success", "message": "交易启动成功"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/stop_trading")
async def stop_grid_trading():
    global trading_bot
    try:
        if not trading_bot:
            return {"status": "error", "message": "没有运行中的交易"}

        await trading_bot.stop()
        trading_bot = None
        return {"status": "success", "message": "交易停止成功"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    # 添加CORS中间件
    from fastapi.middleware.cors import CORSMiddleware

    # 配置允许的域名
    origins = [
        "http://localhost",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
        "http://tiance.kesug.com",
        "https://tiance.kesug.com",
        "https://tiance666.github.io",
        "*"  # 允许所有域名访问（开发阶段可以使用，生产环境建议移除）
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    uvicorn.run(app, host=args.host, port=args.port)
"""
        
        # 写入新的app.py
        stdin, stdout, stderr = ssh.exec_command('cat > /home/trading/grid-trading/src/server/app.py', get_pty=True)
        stdin.write(config)
        stdin.close()
        
        print("更新app.py完成")
        
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
    fix_app() 
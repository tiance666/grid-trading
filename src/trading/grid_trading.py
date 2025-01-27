import asyncio
from decimal import Decimal, ROUND_DOWN
import logging

class GridTradingStrategy:
    def __init__(self, exchange_api, symbol, grid_height, total_grids, investment, 
                 per_grid_amount=None, is_futures=False, leverage=1):
        self.exchange = exchange_api
        self.symbol = symbol
        self.grid_height = grid_height
        self.total_grids = total_grids
        self.investment = investment
        self.per_grid_amount = per_grid_amount
        self.is_futures = is_futures
        self.leverage = leverage
        self.active_orders = {}
        self.is_running = False
        
    async def setup_futures(self):
        """设置合约参数"""
        if self.is_futures:
            await self.exchange.init_futures_position(self.symbol)
            await self.exchange.set_leverage(self.symbol, self.leverage)
        
    def calculate_grid_prices(self, current_price):
        """计算网格价格"""
        price_range = current_price * (self.grid_height / 100)
        grid_interval = price_range / self.total_grids
        
        grid_prices = []
        for i in range(self.total_grids + 1):
            price = current_price - (price_range / 2) + (i * grid_interval)
            # 根据不同交易对调整价格精度
            if self.symbol == "BTCUSDT":
                price = round(price, 1)  # BTC价格精度为0.1
            elif self.symbol == "ETHUSDT":
                price = round(price, 2)  # ETH价格精度为0.01
            grid_prices.append(price)
            
        return grid_prices
        
    def calculate_quantity(self, price):
        """计算每个网格的交易数量"""
        try:
            if self.per_grid_amount:
                quantity = self.per_grid_amount
            else:
                # 计算每格投资金额
                grid_investment = self.investment / self.total_grids
                
                # 合约交易下,实际投资金额需要除以杠杆倍数
                if self.is_futures:
                    actual_investment = grid_investment / self.leverage
                else:
                    actual_investment = grid_investment
                    
                quantity = actual_investment / price

            # 设置最小交易量为0.002 BTC
            if self.symbol == "BTCUSDT":
                min_qty = 0.002
                precision = 3
            elif self.symbol == "ETHUSDT":
                min_qty = 0.01
                precision = 2
            else:
                min_qty = 0.00001
                precision = 5

            # 确保数量不小于最小交易量
            quantity = max(float(Decimal(str(quantity)).quantize(Decimal(str(min_qty)), rounding=ROUND_DOWN)), min_qty)
            
            # 确保返回的是字符串格式
            return f"{quantity:.{precision}f}"
            
        except Exception as e:
            logging.error(f"计算交易数量失败: {str(e)}")
            raise Exception(f"计算交易数量失败: {str(e)}")
        
    async def setup_grids(self):
        """设置网格"""
        try:
            if self.is_futures:
                await self.setup_futures()
                
            current_price = await self.exchange.get_price(self.symbol, self.is_futures)
            grid_prices = self.calculate_grid_prices(current_price)
            
            for i in range(len(grid_prices) - 1):
                buy_price = grid_prices[i]
                sell_price = grid_prices[i + 1]
                quantity = self.calculate_quantity(buy_price)
                
                # 创建买单
                buy_order = await self.exchange.create_order(
                    symbol=self.symbol,
                    side='BUY',
                    order_type='LIMIT',
                    quantity=quantity,
                    price=buy_price,
                    is_futures=self.is_futures
                )
                self.active_orders[buy_order['orderId']] = buy_order
                
                # 创建卖单
                sell_order = await self.exchange.create_order(
                    symbol=self.symbol,
                    side='SELL',
                    order_type='LIMIT',
                    quantity=quantity,
                    price=sell_price,
                    is_futures=self.is_futures
                )
                self.active_orders[sell_order['orderId']] = sell_order
            
        except Exception as e:
            raise Exception(f"设置网格失败: {str(e)}")

    async def monitor_orders(self):
        """监控订单状态"""
        while self.is_running:
            try:
                # 这里可以添加订单状态监控的逻辑
                # 比如检查是否有订单成交，然后创建新的对应订单
                await asyncio.sleep(1)  # 每秒检查一次
            except Exception as e:
                logging.error(f"监控订单出错: {str(e)}")
                await asyncio.sleep(5)  # 出错后等待5秒再继续
            
    async def start(self):
        """启动网格交易"""
        try:
            if self.is_running:
                raise Exception("交易已在运行中")
                
            self.is_running = True
            logging.info(f"开始{self.symbol}的网格交易")
            
            # 如果是合约交易，需要先进行初始化设置
            if self.is_futures:
                # 初始化合约仓位
                await self.exchange.init_futures_position(self.symbol)
                # 设置杠杆倍数
                await self.exchange.set_leverage(self.symbol, self.leverage)
                
            # 获取当前价格
            self.current_price = await self.exchange.get_price(self.symbol, self.is_futures)
            if not self.current_price:
                raise Exception("无法获取当前价格")
                
            # 计算网格价格并设置订单
            await self.setup_grids()
            
            # 启动订单监控
            self.monitor_task = asyncio.create_task(self.monitor_orders())
            logging.info("网格交易启动成功")
            
        except Exception as e:
            self.is_running = False
            logging.error(f"启动网格交易失败: {str(e)}")
            raise
        
    async def stop(self):
        """停止网格交易"""
        self.is_running = False
        # 取消所有活动订单
        for order_id in list(self.active_orders.keys()):
            try:
                await self.exchange.cancel_order(
                    self.symbol, 
                    order_id,
                    is_futures=self.is_futures
                )
                del self.active_orders[order_id]
            except Exception as e:
                logging.error(f"取消订单失败: {str(e)}") 
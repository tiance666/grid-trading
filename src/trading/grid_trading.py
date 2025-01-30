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
        if self.per_grid_amount:
            return self.per_grid_amount
            
        grid_investment = self.investment / self.total_grids
        if self.is_futures:
            grid_investment *= self.leverage
            
        quantity = grid_investment / price
        # 根据不同交易对调整数量精度
        if self.symbol == "BTCUSDT":
            return float(Decimal(str(quantity)).quantize(Decimal('0.001'), rounding=ROUND_DOWN))
        elif self.symbol == "ETHUSDT":
            return float(Decimal(str(quantity)).quantize(Decimal('0.01'), rounding=ROUND_DOWN))
        return float(Decimal(str(quantity)).quantize(Decimal('0.00001'), rounding=ROUND_DOWN))
        
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
        if self.is_running:
            return
            
        self.is_running = True
        await self.setup_grids()
        asyncio.create_task(self.monitor_orders())
        
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
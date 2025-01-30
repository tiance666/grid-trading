from binance.client import Client
from binance.exceptions import BinanceAPIException
import pandas as pd
import ta  # 使用 ta 包而不是 ta-lib
from datetime import datetime
import os
from typing import List, Dict, Any
import logging
import time
import hmac
import hashlib
import asyncio

class BinanceAPI:
    def __init__(self, api_key=None, api_secret=None):
        self.api_key = api_key or os.getenv("BINANCE_API_KEY")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET")
        
        # 初始化客户端
        if self.api_key and self.api_secret:
            # 现货API客户端
            self.client = Client(self.api_key, self.api_secret)
            
            # 合约API客户端
            self.futures_client = Client(self.api_key, self.api_secret)
            self.futures_client.API_URL = 'https://fapi.binance.com/fapi'  # 使用主网API
            
            # 设置请求头和时间戳
            self.client.session.headers.update({
                'X-MBX-APIKEY': self.api_key
            })
            self.futures_client.session.headers.update({
                'X-MBX-APIKEY': self.api_key
            })
            
            # 设置时间同步
            self.client.get_server_time()
            self.futures_client.futures_time()
        else:
            self.client = Client(None, None)
            self.futures_client = None
            logging.info("初始化无密钥模式，只能访问公共API")
            
    async def set_leverage(self, symbol, leverage):
        """设置杠杆倍数"""
        try:
            response = self.futures_client.futures_change_leverage(
                symbol=symbol,
                leverage=leverage
            )
            return response
        except BinanceAPIException as e:
            raise Exception(f"设置杠杆倍数失败: {str(e)}")
            
    async def get_price(self, symbol, is_futures=False):
        """获取当前价格"""
        try:
            if is_futures:
                ticker = self.futures_client.futures_symbol_ticker(symbol=symbol)
            else:
                ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except BinanceAPIException as e:
            raise Exception(f"获取价格失败: {str(e)}")
            
    async def create_order(self, symbol, side, order_type, quantity, price=None, is_futures=False):
        """创建订单"""
        try:
            params = {
                'symbol': symbol,
                'side': side.upper(),
                'type': order_type.upper(),
                'quantity': quantity,
            }
            
            if price:
                params['price'] = price
                params['timeInForce'] = 'GTC'
                
            if is_futures:
                order = self.futures_client.futures_create_order(**params)
            else:
                order = self.client.create_order(**params)
            return order
        except BinanceAPIException as e:
            raise Exception(f"创建订单失败: {str(e)}")
            
    async def get_balance(self, asset, is_futures=False):
        """获取资产余额"""
        try:
            if is_futures:
                balance = self.futures_client.futures_account_balance()
                for b in balance:
                    if b['asset'] == asset:
                        return float(b['balance'])
                return 0.0
            else:
                balance = self.client.get_asset_balance(asset=asset)
                return float(balance['free'])
        except BinanceAPIException as e:
            raise Exception(f"获取余额失败: {str(e)}")
            
    async def cancel_order(self, symbol, order_id, is_futures=False):
        """取消订单"""
        try:
            if is_futures:
                return self.futures_client.futures_cancel_order(
                    symbol=symbol,
                    orderId=order_id
                )
            else:
                return self.client.cancel_order(
                    symbol=symbol,
                    orderId=order_id
                )
        except BinanceAPIException as e:
            raise Exception(f"取消订单失败: {str(e)}")

    async def init_futures_position(self, symbol):
        """初始化合约仓位"""
        try:
            # 设置保证金类型为ISOLATED
            try:
                self.futures_client.futures_change_margin_type(
                    symbol=symbol,
                    marginType='ISOLATED'
                )
            except BinanceAPIException as e:
                if e.code != -4046:  # 忽略"已经是这个模式"的错误
                    raise e
                
            return True
        except BinanceAPIException as e:
            raise Exception(f"初始化合约仓位失败: {str(e)}")

    async def get_klines(self, symbol: str, interval: str, limit: int = 1000, start_time: int = None, end_time: int = None):
        """获取K线数据
        
        Args:
            symbol: 交易对
            interval: K线间隔
            limit: 获取数量
            start_time: 开始时间戳（毫秒）
            end_time: 结束时间戳（毫秒）
        """
        try:
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            if start_time:
                params['startTime'] = start_time
            if end_time:
                params['endTime'] = end_time
                
            klines = self.client.get_klines(**params)
            return klines
        except BinanceAPIException as e:
            raise Exception(f"获取K线数据失败: {str(e)}")

    async def get_historical_klines(self, symbol: str, interval: str, start_str: str, end_str: str = None):
        """获取历史K线数据
        
        Args:
            symbol: 交易对
            interval: K线间隔
            start_str: 开始时间，如 "1 Dec, 2017"
            end_str: 结束时间，如 "1 Jan, 2018"，不指定则为当前时间
        """
        try:
            klines = self.client.get_historical_klines(
                symbol=symbol,
                interval=interval,
                start_str=start_str,
                end_str=end_str
            )
            return klines
        except BinanceAPIException as e:
            raise Exception(f"获取历史K线数据失败: {str(e)}")

    async def get_klines_df(self, symbol: str, interval: str, limit: int = 100):
        """获取K线数据并计算技术指标"""
        try:
            # 使用同步客户端获取K线数据
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            # 转换为DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 
                'volume', 'close_time', 'quote_volume', 'trades',
                'taker_buy_base', 'taker_buy_quote', 'ignore'
            ])
            
            # 转换数据类型
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            # 设置索引
            df.set_index('timestamp', inplace=True)
            
            # 计算BOLL指标
            df['bb_upper'] = ta.volatility.bollinger_hband(df['close'])
            df['bb_middle'] = ta.volatility.bollinger_mavg(df['close'])
            df['bb_lower'] = ta.volatility.bollinger_lband(df['close'])
            
            # 计算EMA指标
            df['ema_9'] = ta.trend.ema_indicator(df['close'], window=9)
            df['ema_20'] = ta.trend.ema_indicator(df['close'], window=20)
            
            # 计算MACD指标
            macd = ta.trend.MACD(df['close'])
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            df['macd_hist'] = macd.macd_diff()
            
            # 计算RSI指标
            df['rsi'] = ta.momentum.rsi(df['close'])
            
            return df
            
        except BinanceAPIException as e:
            raise Exception(f"获取K线数据失败: {str(e)}")
            
    async def get_order_status(self, symbol, order_id):
        try:
            order = self.client.get_order(
                symbol=symbol,
                orderId=order_id
            )
            return order['status'].lower()
        except BinanceAPIException as e:
            raise Exception(f"获取订单状态失败: {str(e)}")
            
    async def close(self):
        pass  # 不再需要关闭连接 

    def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """获取未完成订单"""
        try:
            orders = self.client.get_open_orders(symbol=symbol) if symbol else self.client.get_open_orders()
            return orders
        except Exception as e:
            logging.error(f"获取未完成订单失败: {str(e)}")
            raise 

    def _check_auth(self):
        """检查是否有API密钥权限"""
        if not self.api_key or not self.api_secret:
            raise Exception("此操作需要API密钥") 
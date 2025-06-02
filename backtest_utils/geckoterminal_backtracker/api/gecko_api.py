"""
GeckoTerminal API 客户端
用于获取 DEX 交易池的 OHLC 数据
"""

import requests
import pandas as pd
from datetime import datetime
import time


class GeckoTerminalAPI:
    """
    GeckoTerminal API 客户端，用于获取 OHLC 数据
    """
    BASE_URL = "https://api.geckoterminal.com/api/v2"
    
    def __init__(self):
        self.session = requests.Session()
        # 设置请求头，避免被限流
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'GeckoTerminal-Data-Backtracking/1.0'
        })
    
    def get_networks(self):
        """
        获取支持的网络列表
        
        返回:
            list: 网络列表
        """
        url = f"{self.BASE_URL}/networks"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            return data.get('data', [])
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching networks: {e}")
            return []
    
    def get_ohlc(self, network, pool_address, timeframe='day', aggregate=1, 
                 before_timestamp=None, limit=100, currency='usd', token='base',
                 include_empty_intervals=False):
        """
        获取池子的 OHLC 数据
        
        参数:
            network (str): 网络 ID，例如 'eth', 'bsc'
            pool_address (str): 池子地址
            timeframe (str): 时间周期，可选 'day', 'hour', 'minute'
            aggregate (int): 聚合周期，例如 timeframe='minute', aggregate=15 表示 15分钟K线
            before_timestamp (int): 返回此时间戳之前的数据（Unix 时间戳，秒）
            limit (int): 返回结果数量限制，默认100，最大1000
            currency (str): 返回的价格单位，'usd' 或 'token'
            token (str): 返回基础代币或报价代币的 OHLC，'base', 'quote' 或代币地址
            include_empty_intervals (bool): 是否填充空时间间隔
            
        返回:
            pandas.DataFrame: OHLC 数据，包含 timestamp, open, high, low, close, volume 列
        """
        url = f"{self.BASE_URL}/networks/{network}/pools/{pool_address}/ohlcv/{timeframe}"
        
        params = {
            'aggregate': aggregate,
            'limit': limit,
            'currency': currency,
            'token': token,
            'include_empty_intervals': str(include_empty_intervals).lower()
        }
        
        if before_timestamp:
            params['before_timestamp'] = before_timestamp
            
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()  # 如果请求失败，抛出异常
            
            data = response.json()
            
            # 检查是否有数据
            if 'data' not in data or 'attributes' not in data['data'] or 'ohlcv_list' not in data['data']['attributes']:
                print(f"No OHLC data found for pool {pool_address} on {network}")
                return pd.DataFrame()
                
            # 提取 OHLC 数据
            ohlcv_list = data['data']['attributes']['ohlcv_list']
            
            # 创建 DataFrame
            df = pd.DataFrame(ohlcv_list, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # 转换时间戳为 datetime
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
            
            # 提取代币信息
            if 'meta' in data:
                base_token = data['meta'].get('base', {})
                quote_token = data['meta'].get('quote', {})
                
                # 添加代币信息列
                df['base_token_address'] = base_token.get('address', '')
                df['base_token_name'] = base_token.get('name', '')
                df['base_token_symbol'] = base_token.get('symbol', '')
                
                df['quote_token_address'] = quote_token.get('address', '')
                df['quote_token_name'] = quote_token.get('name', '')
                df['quote_token_symbol'] = quote_token.get('symbol', '')
            
            return df
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching OHLC data: {e}")
            return pd.DataFrame()
    
    def get_pool_info(self, network, pool_address):
        """
        获取池子信息
        
        参数:
            network (str): 网络 ID
            pool_address (str): 池子地址
            
        返回:
            dict: 池子信息
        """
        url = f"{self.BASE_URL}/networks/{network}/pools/{pool_address}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            return data.get('data', {})
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching pool info: {e}")
            return {}
    
    def search_pools(self, network=None, query=None, page=1, per_page=20, include=None):
        """
        搜索池子
        
        参数:
            network (str, optional): 网络 ID，如果不提供则搜索所有网络
            query (str): 搜索关键词 (pool address, token address, or token symbol)
            page (int): 页码，默认为1
            per_page (int): 每页结果数，默认为20 (API限制最大20)
            include (list, optional): 要包含的相关资源，如 ['base_token', 'quote_token', 'dex']
            
        返回:
            list: 池子列表
        """
        url = f"{self.BASE_URL}/search/pools"
        
        params = {
            'page': page
        }
        
        # 添加查询参数
        if query:
            params['query'] = query
            
        # 添加网络过滤（可选）
        if network:
            params['network'] = network
            
        # 添加包含的相关资源
        if include:
            params['include'] = ','.join(include)
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get('data', [])
            
        except requests.exceptions.RequestException as e:
            print(f"Error searching pools: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response text: {e.response.text}")
            return []
    
    def get_trending_pools(self, network, page=1, per_page=100):
        """
        获取热门池子
        
        参数:
            network (str): 网络 ID
            page (int): 页码
            per_page (int): 每页结果数
            
        返回:
            list: 热门池子列表
        """
        url = f"{self.BASE_URL}/networks/{network}/trending_pools"
        
        params = {
            'page': page,
            'per_page': per_page
        }
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get('data', [])
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching trending pools: {e}")
            return []

"""
数据获取模块
用于从 GeckoTerminal API 获取历史 OHLC 数据
"""

import time
from datetime import datetime
import pandas as pd

from ..api.gecko_api import GeckoTerminalAPI


class OHLCDataFetcher:
    """
    OHLC 数据获取类
    用于从 GeckoTerminal API 获取历史 OHLC 数据
    """
    def __init__(self, api=None):
        """
        初始化数据获取器
        
        参数:
            api (GeckoTerminalAPI): API 客户端，如果为 None 则创建新的客户端
        """
        self.api = api or GeckoTerminalAPI()
    
    def fetch_historical_ohlc(self, network, pool_address, timeframe='day', aggregate=1, 
                             days_back=30, request_delay=2):
        """
        获取历史 OHLC 数据
        
        参数:
            network (str): 网络 ID
            pool_address (str): 池子地址
            timeframe (str): 时间周期 ('day', 'hour', 'minute')
            aggregate (int): 聚合周期
            days_back (int): 回溯天数
            request_delay (float): 请求延迟，单位为秒，用于避免 API 限流
            
        返回:
            pandas.DataFrame: 历史 OHLC 数据
        """
        # 计算起始时间戳 (当前时间 - days_back 天)
        end_timestamp = int(time.time())
        
        all_data = pd.DataFrame()
        current_timestamp = end_timestamp
        
        # 循环获取所有历史数据
        while True:
            print(f"Fetching data before timestamp {current_timestamp} ({datetime.fromtimestamp(current_timestamp)})")
            
            # 获取一批数据
            df = self.api.get_ohlc(
                network=network,
                pool_address=pool_address,
                timeframe=timeframe,
                aggregate=aggregate,
                before_timestamp=current_timestamp,
                limit=1000,  # 获取最大数量
                include_empty_intervals=True
            )
            
            if df.empty:
                break
                
            # 合并数据
            all_data = pd.concat([all_data, df])
            
            # 获取最早的时间戳作为下一次请求的 before_timestamp
            earliest_timestamp = df['timestamp'].min()
            
            # 如果已经获取了足够早的数据，或者没有更早的数据，则退出循环
            days_fetched = (end_timestamp - earliest_timestamp) / (24 * 3600)
            if days_fetched >= days_back or current_timestamp == earliest_timestamp:
                break
                
            # 更新时间戳，继续获取更早的数据
            current_timestamp = earliest_timestamp - 1
            
            # 避免请求过于频繁，API 限制为每分钟 30 次请求
            time.sleep(request_delay)
        
        # 去重并按时间排序
        if not all_data.empty:
            all_data = all_data.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
            
        return all_data
    
    def fetch_and_store(self, network, pool_address, timeframe='day', aggregate=1, 
                       days_back=30, storage_handlers=None):
        """
        获取历史 OHLC 数据并存储
        
        参数:
            network (str): 网络 ID
            pool_address (str): 池子地址
            timeframe (str): 时间周期 ('day', 'hour', 'minute')
            aggregate (int): 聚合周期
            days_back (int): 回溯天数
            storage_handlers (list): 存储处理器列表，每个处理器必须有 save_ohlc 方法
            
        返回:
            pandas.DataFrame: 历史 OHLC 数据
        """
        # 获取数据
        df = self.fetch_historical_ohlc(
            network=network,
            pool_address=pool_address,
            timeframe=timeframe,
            aggregate=aggregate,
            days_back=days_back
        )
        
        # 存储数据
        if storage_handlers and not df.empty:
            for handler in storage_handlers:
                handler.save_ohlc(df, network, pool_address, timeframe, aggregate)
        
        return df

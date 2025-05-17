"""
CSV 存储模块
用于将数据保存为 CSV 文件
"""

import os
import pandas as pd


class CSVStorage:
    """
    CSV 存储类，用于将数据保存为 CSV 文件
    """
    def __init__(self, base_dir='data'):
        """
        初始化 CSV 存储
        
        参数:
            base_dir (str): 基础目录
        """
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
    
    def save_ohlc(self, df, network, pool_address, timeframe, aggregate):
        """
        保存 OHLC 数据到 CSV 文件
        
        参数:
            df (pandas.DataFrame): OHLC 数据
            network (str): 网络 ID
            pool_address (str): 池子地址
            timeframe (str): 时间周期
            aggregate (int): 聚合周期
        """
        if df.empty:
            print("No data to save")
            return
            
        # 创建网络目录
        network_dir = os.path.join(self.base_dir, network)
        os.makedirs(network_dir, exist_ok=True)
        
        # 创建池子目录
        pool_dir = os.path.join(network_dir, pool_address)
        os.makedirs(pool_dir, exist_ok=True)
        
        # 文件名格式: {timeframe}_{aggregate}.csv
        filename = f"{timeframe}_{aggregate}.csv"
        filepath = os.path.join(pool_dir, filename)
        
        # 保存到 CSV
        df.to_csv(filepath, index=False)
        print(f"Data saved to {filepath}")
        
        return filepath
    
    def load_ohlc(self, network, pool_address, timeframe, aggregate):
        """
        从 CSV 文件加载 OHLC 数据
        
        参数:
            network (str): 网络 ID
            pool_address (str): 池子地址
            timeframe (str): 时间周期
            aggregate (int): 聚合周期
            
        返回:
            pandas.DataFrame: OHLC 数据
        """
        # 文件路径
        filepath = os.path.join(self.base_dir, network, pool_address, f"{timeframe}_{aggregate}.csv")
        
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            return pd.DataFrame()
            
        # 加载 CSV
        df = pd.read_csv(filepath)
        
        # 转换时间戳为 datetime
        if 'timestamp' in df.columns and 'datetime' not in df.columns:
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
            
        return df
    
    def list_available_data(self):
        """
        列出可用的数据
        
        返回:
            list: 可用数据列表，每项包含 network, pool_address, timeframe, aggregate
        """
        result = []
        
        # 遍历网络目录
        for network in os.listdir(self.base_dir):
            network_dir = os.path.join(self.base_dir, network)
            
            if not os.path.isdir(network_dir):
                continue
                
            # 遍历池子目录
            for pool_address in os.listdir(network_dir):
                pool_dir = os.path.join(network_dir, pool_address)
                
                if not os.path.isdir(pool_dir):
                    continue
                    
                # 遍历 CSV 文件
                for filename in os.listdir(pool_dir):
                    if not filename.endswith('.csv'):
                        continue
                        
                    # 解析文件名
                    parts = filename.split('.')[0].split('_')
                    
                    if len(parts) != 2:
                        continue
                        
                    timeframe, aggregate = parts
                    
                    result.append({
                        'network': network,
                        'pool_address': pool_address,
                        'timeframe': timeframe,
                        'aggregate': int(aggregate)
                    })
        
        return result

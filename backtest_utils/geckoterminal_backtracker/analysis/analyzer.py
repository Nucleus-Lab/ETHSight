"""
OHLC 数据分析模块
用于分析价格数据和应用技术指标
"""

import pandas as pd
import numpy as np
import os
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from .ai_indicator_generator import AIIndicatorGenerator
from .plotly_visualizer import plot_with_indicators
import plotly.io as pio

class OHLCAnalyzer:
    """
    OHLC 数据分析类
    用于分析价格数据和应用技术指标
    """
    
    def __init__(self, df: pd.DataFrame, api_key: Optional[str] = None):
        """
        初始化分析器
        
        参数:
            df (pandas.DataFrame): 包含 OHLC 数据的 DataFrame
            api_key (str, optional): OpenAI API 密钥
        """
        self.df = df.copy()
        
        # 确保 datetime 列是 datetime 类型
        if 'datetime' in self.df.columns:
            self.df['datetime'] = pd.to_datetime(self.df['datetime'])
            
        # 初始化 AI 指标生成器
        try:
            self.ai_generator = AIIndicatorGenerator(api_key)
        except ValueError:
            self.ai_generator = None
            print("警告: 未提供 OpenAI API 密钥，AI 指标生成功能将不可用")
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        获取数据的统计摘要
        
        返回:
            dict: 统计数据
        """
        # 确保 datetime 列是 datetime 类型
        if 'datetime' in self.df.columns:
            self.df['datetime'] = pd.to_datetime(self.df['datetime'])
        
        start_date = self.df['datetime'].min()
        end_date = self.df['datetime'].max()
        days = (end_date - start_date).days
        
        # 计算价格变化
        first_price = self.df['close'].iloc[0]
        last_price = self.df['close'].iloc[-1]
        price_change = last_price - first_price
        price_change_pct = (price_change / first_price) * 100 if first_price != 0 else 0
        
        # 计算日收益率
        self.df['daily_return'] = self.df['close'].pct_change() * 100
        
        # 计算波动率 (收盘价的标准差)
        volatility = self.df['daily_return'].std()
        
        return {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'days': days,
            'data_points': len(self.df),
            'price_change': price_change,
            'price_change_pct': price_change_pct,
            'high_max': self.df['high'].max(),
            'high_date': self.df.loc[self.df['high'].idxmax(), 'datetime'].strftime('%Y-%m-%d'),
            'low_min': self.df['low'].min(),
            'low_date': self.df.loc[self.df['low'].idxmin(), 'datetime'].strftime('%Y-%m-%d'),
            'volume_total': self.df['volume'].sum(),
            'volatility_avg': volatility,
            'daily_return_avg': self.df['daily_return'].mean(),
            'daily_return_std': self.df['daily_return'].std()
        }
    
    def create_ai_indicator(self, description: str, model: str = "gpt-4.1") -> pd.DataFrame:
        """
        使用 AI 创建并应用自定义指标
        
        参数:
            description (str): 指标的自然语言描述
            model (str): 要使用的 OpenAI 模型
            
        返回:
            pandas.DataFrame: 添加了指标的 DataFrame
        """
        if self.ai_generator is None:
            raise ValueError("AI 指标生成器未初始化，请提供有效的 OpenAI API 密钥")
        
        # 生成并应用指标
        result_df = self.ai_generator.apply_indicator(self.df, description, model)
        
        # 更新内部 DataFrame
        self.df = result_df
        
        return result_df
    
    def save_ai_indicator(self, description: str, name: str, directory: str = "indicators") -> str:
        """
        生成并保存自定义指标
        
        参数:
            description (str): 指标的自然语言描述
            name (str): 指标名称
            directory (str): 保存目录
            
        返回:
            str: 保存的文件路径
        """
        if self.ai_generator is None:
            raise ValueError("AI 指标生成器未初始化，请提供有效的 OpenAI API 密钥")
        
        # 生成指标代码
        code = self.ai_generator.generate_indicator_code(description)
        
        # 保存指标
        file_path = self.ai_generator.save_indicator(description, code, name, directory)
        
        return file_path
    
    def plot_with_indicators(self, indicators: List[str], title: Optional[str] = None, 
                            save_path: Optional[str] = None, show: bool = True,
                            save_json: Optional[str] = None, timeframe: str = 'day',
                            aggregate: int = 1) -> None:
        """
        绘制带有指标的交互式图表
        
        参数:
            indicators (list): 要显示的指标列名列表
            title (str, optional): 图表标题
            save_path (str, optional): 保存路径 (HTML 文件)
            show (bool): 是否显示图表
            save_json (str, optional): JSON 格式保存路径
            timeframe (str): 时间周期 (minute, hour, day)
            aggregate (int): 聚合周期
        """
        # 调用 plotly_visualizer 模块中的函数
        return plot_with_indicators(self.df, indicators, title, save_path, show, save_json, timeframe, aggregate)

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
                            save_path: Optional[str] = None, show: bool = False,
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

# """
# OHLC 数据分析模块
# 用于分析价格数据和应用技术指标
# """

# import pandas as pd
# import numpy as np
# import matplotlib.pyplot as plt
# import os
# from typing import List, Dict, Any, Optional, Union
# from datetime import datetime

# from .ai_indicator_generator import AIIndicatorGenerator

# class OHLCAnalyzer:
#     """
#     OHLC 数据分析类
#     用于分析价格数据和应用技术指标
#     """
    
#     def __init__(self, df: pd.DataFrame, api_key: Optional[str] = None):
#         """
#         初始化分析器
        
#         参数:
#             df (pandas.DataFrame): 包含 OHLC 数据的 DataFrame
#             api_key (str, optional): OpenAI API 密钥
#         """
#         self.df = df.copy()
        
#         # 确保 datetime 列是 datetime 类型
#         if 'datetime' in self.df.columns:
#             self.df['datetime'] = pd.to_datetime(self.df['datetime'])
            
#         # 初始化 AI 指标生成器
#         try:
#             self.ai_generator = AIIndicatorGenerator(api_key)
#         except ValueError:
#             self.ai_generator = None
#             print("警告: 未提供 OpenAI API 密钥，AI 指标生成功能将不可用")
    
#     def get_summary_stats(self) -> Dict[str, Any]:
#         """
#         获取数据的统计摘要
        
#         返回:
#             dict: 统计数据
#         """
#         # 确保 datetime 列是 datetime 类型
#         if 'datetime' in self.df.columns:
#             self.df['datetime'] = pd.to_datetime(self.df['datetime'])
        
#         start_date = self.df['datetime'].min()
#         end_date = self.df['datetime'].max()
#         days = (end_date - start_date).days
        
#         # 计算价格变化
#         first_price = self.df['close'].iloc[0]
#         last_price = self.df['close'].iloc[-1]
#         price_change = last_price - first_price
#         price_change_pct = (price_change / first_price) * 100 if first_price != 0 else 0
        
#         # 计算日收益率
#         self.df['daily_return'] = self.df['close'].pct_change() * 100
        
#         # 计算波动率 (收盘价的标准差)
#         volatility = self.df['daily_return'].std()
        
#         return {
#             'start_date': start_date.strftime('%Y-%m-%d'),
#             'end_date': end_date.strftime('%Y-%m-%d'),
#             'days': days,
#             'data_points': len(self.df),
#             'price_change': price_change,
#             'price_change_pct': price_change_pct,
#             'high_max': self.df['high'].max(),
#             'high_date': self.df.loc[self.df['high'].idxmax(), 'datetime'].strftime('%Y-%m-%d'),
#             'low_min': self.df['low'].min(),
#             'low_date': self.df.loc[self.df['low'].idxmin(), 'datetime'].strftime('%Y-%m-%d'),
#             'volume_total': self.df['volume'].sum(),
#             'volatility_avg': volatility,
#             'daily_return_avg': self.df['daily_return'].mean(),
#             'daily_return_std': self.df['daily_return'].std()
#         }
    
#     def create_ai_indicator(self, description: str, model: str = "gpt-4.1") -> pd.DataFrame:
#         """
#         使用 AI 创建并应用自定义指标
        
#         参数:
#             description (str): 指标的自然语言描述
#             model (str): 要使用的 OpenAI 模型
            
#         返回:
#             pandas.DataFrame: 添加了指标的 DataFrame
#         """
#         if self.ai_generator is None:
#             raise ValueError("AI 指标生成器未初始化，请提供有效的 OpenAI API 密钥")
        
#         # 生成并应用指标
#         result_df = self.ai_generator.apply_indicator(self.df, description, model)
        
#         # 更新内部 DataFrame
#         self.df = result_df
        
#         return result_df
    
#     def save_ai_indicator(self, description: str, name: str, directory: str = "indicators") -> str:
#         """
#         生成并保存自定义指标
        
#         参数:
#             description (str): 指标的自然语言描述
#             name (str): 指标名称
#             directory (str): 保存目录
            
#         返回:
#             str: 保存的文件路径
#         """
#         if self.ai_generator is None:
#             raise ValueError("AI 指标生成器未初始化，请提供有效的 OpenAI API 密钥")
        
#         # 生成指标代码
#         code = self.ai_generator.generate_indicator_code(description)
        
#         # 保存指标
#         file_path = self.ai_generator.save_indicator(description, code, name, directory)
        
#         return file_path
    
#     def plot_data(self, title: Optional[str] = None, save_path: Optional[str] = None, 
#                  figsize: tuple = (12, 8), show_volume: bool = True) -> None:
#         """
#         绘制 OHLC 数据图表
        
#         参数:
#             title (str, optional): 图表标题
#             save_path (str, optional): 保存路径
#             figsize (tuple): 图表大小
#             show_volume (bool): 是否显示成交量
#         """
#         # 确定子图数量
#         n_subplots = 1 + int(show_volume)
        
#         # 创建图表
#         fig, axes = plt.subplots(n_subplots, 1, figsize=figsize, sharex=True, 
#                                 gridspec_kw={'height_ratios': [3] + [1] * (n_subplots - 1)})
        
#         if n_subplots == 1:
#             axes = [axes]
        
#         # 绘制价格
#         ax_price = axes[0]
#         ax_price.plot(self.df['datetime'], self.df['close'], label='Close Price')
        
#         # 设置标题
#         if title:
#             ax_price.set_title(title)
#         else:
#             # 尝试从数据中提取代币信息
#             if 'base_token_symbol' in self.df.columns and 'quote_token_symbol' in self.df.columns:
#                 base = self.df['base_token_symbol'].iloc[0] if not pd.isna(self.df['base_token_symbol'].iloc[0]) else 'Base'
#                 quote = self.df['quote_token_symbol'].iloc[0] if not pd.isna(self.df['quote_token_symbol'].iloc[0]) else 'Quote'
#                 ax_price.set_title(f"{base}/{quote} Price Analysis")
#             else:
#                 ax_price.set_title("Price Analysis")
        
#         ax_price.set_ylabel('Price')
#         ax_price.legend()
#         ax_price.grid(True, alpha=0.3)
        
#         # 绘制成交量
#         if show_volume:
#             ax_volume = axes[1]
#             ax_volume.bar(self.df['datetime'], self.df['volume'], alpha=0.5, color='blue', label='Volume')
#             ax_volume.set_ylabel('Volume')
#             ax_volume.grid(True, alpha=0.3)
        
#         # 格式化 x 轴日期
#         plt.xticks(rotation=45)
#         plt.tight_layout()
        
#         # 保存图表
#         if save_path:
#             plt.savefig(save_path)
#             print(f"图表已保存到 {save_path}")
        
#         # 显示图表
#         plt.show()
    
#     def plot_with_indicators(self, indicators: List[str], title: Optional[str] = None, 
#                            save_path: Optional[str] = None, figsize: tuple = (12, 10)) -> None:
#         """
#         绘制带有指标的图表
        
#         参数:
#             indicators (list): 要显示的指标列名列表
#             title (str, optional): 图表标题
#             save_path (str, optional): 保存路径
#             figsize (tuple): 图表大小
#         """
#         # 验证指标是否存在
#         missing_indicators = [ind for ind in indicators if ind not in self.df.columns]
#         if missing_indicators:
#             raise ValueError(f"以下指标不存在于数据中: {', '.join(missing_indicators)}")
        
#         # 检查是否有信号指标
#         signal_indicators = []
#         for ind in indicators:
#             # 如果指标名称中包含信号、买入或卖出，或者数据类型是布尔型或整数型且只有 0 和 1
#             if ('signal' in ind.lower() or 'buy' in ind.lower() or 'sell' in ind.lower() or 
#                 '信号' in ind or '买入' in ind or '卖出' in ind):
#                 signal_indicators.append(ind)
#             elif self.df[ind].dtype in ['bool', 'int64', 'int32'] and set(self.df[ind].unique()).issubset({0, 1, True, False}):
#                 signal_indicators.append(ind)
        
#         # 确定子图数量
#         n_subplots = 2 + len(indicators) - len(signal_indicators)  # 价格 + 成交量 + 非信号指标
        
#         # 创建图表
#         fig, axes = plt.subplots(n_subplots, 1, figsize=figsize, sharex=True, 
#                                 gridspec_kw={'height_ratios': [3, 1] + [1] * (len(indicators) - len(signal_indicators))})
        
#         # 绘制价格
#         ax_price = axes[0]
#         ax_price.plot(self.df['datetime'], self.df['close'], label='Close Price')
        
#         # 在价格图上标记信号
#         for signal_ind in signal_indicators:
#             # 找到信号点
#             signal_df = self.df.copy()
            
#             # 如果是布尔型或整数型，将其转换为布尔型
#             if signal_df[signal_ind].dtype in ['int64', 'int32']:
#                 buy_signals = signal_df[signal_df[signal_ind] == 1]
#                 sell_signals = signal_df[signal_df[signal_ind] == -1] if -1 in signal_df[signal_ind].values else pd.DataFrame()
#             elif signal_df[signal_ind].dtype == 'bool':
#                 buy_signals = signal_df[signal_df[signal_ind] == True]
#                 sell_signals = pd.DataFrame()  # 布尔型通常只有买入信号
#             else:
#                 # 如果是浮点型，尝试使用阈值
#                 threshold = 0.5
#                 buy_signals = signal_df[signal_df[signal_ind] > threshold]
#                 sell_signals = signal_df[signal_df[signal_ind] < -threshold] if signal_df[signal_ind].min() < 0 else pd.DataFrame()
            
#             # 实现现货交易逻辑：只有买入后才能卖出
#             valid_buy_signals = []
#             valid_sell_signals = []
#             in_position = False
#             entry_price = 0
            
#             # 按时间排序所有信号
#             all_signals = pd.DataFrame()
#             if not buy_signals.empty:
#                 buy_signals['signal_type'] = 'buy'
#                 all_signals = pd.concat([all_signals, buy_signals])
#             if not sell_signals.empty:
#                 sell_signals['signal_type'] = 'sell'
#                 all_signals = pd.concat([all_signals, sell_signals])
            
#             # 按时间排序
#             if not all_signals.empty:
#                 all_signals = all_signals.sort_values('datetime')
                
#                 # 遍历所有信号，模拟交易
#                 for idx, row in all_signals.iterrows():
#                     if row['signal_type'] == 'buy' and not in_position:
#                         # 买入信号，且当前没有持仓
#                         valid_buy_signals.append(row)
#                         in_position = True
#                         entry_price = row['close']
#                     elif row['signal_type'] == 'sell' and in_position:
#                         # 卖出信号，且当前有持仓
#                         valid_sell_signals.append(row)
#                         in_position = False
            
#             # 将有效信号转换回 DataFrame
#             valid_buy_df = pd.DataFrame(valid_buy_signals) if valid_buy_signals else pd.DataFrame()
#             valid_sell_df = pd.DataFrame(valid_sell_signals) if valid_sell_signals else pd.DataFrame()
            
#             # 标记买入信号
#             if not valid_buy_df.empty:
#                 ax_price.scatter(valid_buy_df['datetime'], valid_buy_df['close'], 
#                               marker='^', color='green', s=100, label=f'{signal_ind} Buy Signal')
            
#             # 标记卖出信号
#             if not valid_sell_df.empty:
#                 ax_price.scatter(valid_sell_df['datetime'], valid_sell_df['close'], 
#                               marker='v', color='red', s=100, label=f'{signal_ind} Sell Signal')
                
#             # 计算并显示交易统计
#             if not valid_buy_df.empty and not valid_sell_df.empty:
#                 # 计算盈利率
#                 total_trades = len(valid_sell_df)
#                 profitable_trades = sum(valid_sell_df['close'].values > valid_buy_df['close'].values[:len(valid_sell_df)])
#                 win_rate = profitable_trades / total_trades * 100 if total_trades > 0 else 0
                
#                 # 计算总收益
#                 returns = []
#                 for i in range(min(len(valid_buy_df), len(valid_sell_df))):
#                     buy_price = valid_buy_df.iloc[i]['close']
#                     sell_price = valid_sell_df.iloc[i]['close']
#                     returns.append((sell_price - buy_price) / buy_price * 100)
                
#                 total_return = sum(returns)
#                 avg_return = total_return / len(returns) if returns else 0
                
#                 # 添加统计信息到图表中
#                 stats_text = f"\nTrades: {total_trades}, Win Rate: {win_rate:.2f}%, Total Return: {total_return:.2f}%, Avg Return: {avg_return:.2f}%"
#                 ax_price.text(0.02, 0.02, stats_text, transform=ax_price.transAxes, bbox=dict(facecolor='white', alpha=0.7))
        
#         # 设置标题
#         if title:
#             ax_price.set_title(title)
#         else:
#             # 尝试从数据中提取代币信息
#             if 'base_token_symbol' in self.df.columns and 'quote_token_symbol' in self.df.columns:
#                 base = self.df['base_token_symbol'].iloc[0] if not pd.isna(self.df['base_token_symbol'].iloc[0]) else 'Base'
#                 quote = self.df['quote_token_symbol'].iloc[0] if not pd.isna(self.df['quote_token_symbol'].iloc[0]) else 'Quote'
#                 ax_price.set_title(f"{base}/{quote} Technical Analysis")
#             else:
#                 ax_price.set_title("Technical Analysis")
        
#         ax_price.set_ylabel('Price')
#         ax_price.legend()
#         ax_price.grid(True, alpha=0.3)
        
#         # 绘制成交量
#         ax_volume = axes[1]
#         ax_volume.bar(self.df['datetime'], self.df['volume'], alpha=0.5, color='blue', label='Volume')
#         ax_volume.set_ylabel('Volume')
#         ax_volume.grid(True, alpha=0.3)
        
#         # 绘制非信号指标
#         non_signal_indicators = [ind for ind in indicators if ind not in signal_indicators]
#         for i, indicator in enumerate(non_signal_indicators):
#             ax_ind = axes[i + 2]
#             ax_ind.plot(self.df['datetime'], self.df[indicator], label=indicator)
#             ax_ind.set_ylabel(indicator)
#             ax_ind.legend()
#             ax_ind.grid(True, alpha=0.3)
        
#         # 格式化 x 轴日期
#         plt.xticks(rotation=45)
#         plt.tight_layout()
        
#         # 保存图表
#         if save_path:
#             plt.savefig(save_path)
#             print(f"图表已保存到 {save_path}")
        
#         # 显示图表
#         plt.show()

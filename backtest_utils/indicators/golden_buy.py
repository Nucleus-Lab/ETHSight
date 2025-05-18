import pandas as pd
import numpy as np

def calculate_golden_cross_signal(df):
    """
    计算黄金交叉买入信号
    
    黄金交叉是一种技术分析模式，通常发生在短期移动平均线（如 50 日均线）上穿长期移动平均线（如 200 日均线）时。
    这种交叉被认为是一个买入信号。
    
    参数:
        df (pandas.DataFrame): 包含 OHLC 和成交量数据的 DataFrame
        
    返回:
        pandas.DataFrame: 添加了 'buy_signal' 和 'sell_signal' 列的 DataFrame
    """
    # 计算短期和长期移动平均线
    df['short_ma'] = df['close'].rolling(window=10, min_periods=1).mean()
    df['long_ma'] = df['close'].rolling(window=20, min_periods=1).mean()
    
    # 初始化信号列
    df['buy_signal'] = 0
    df['sell_signal'] = 0
    
    # 生成买入信号：短期均线上穿长期均线
    df.loc[(df['short_ma'] > df['long_ma']) & (df['short_ma'].shift(1) <= df['long_ma'].shift(1)), 'buy_signal'] = 1
    
    # 删除临时列
    df.drop(columns=['short_ma', 'long_ma'], inplace=True)
    
    return df

calculate_golden_cross_signal(df)
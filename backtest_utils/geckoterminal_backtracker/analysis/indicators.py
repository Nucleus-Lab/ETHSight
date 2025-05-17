"""
指标模块
包含常用的技术指标计算函数
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Union

def calculate_sma(df: pd.DataFrame, period: int = 20, column: str = 'close') -> pd.DataFrame:
    """
    计算简单移动平均线 (SMA)
    
    参数:
        df (pandas.DataFrame): 包含 OHLC 数据的 DataFrame
        period (int): 移动平均周期
        column (str): 用于计算的列名
        
    返回:
        pandas.DataFrame: 添加了 SMA 列的 DataFrame
    """
    df[f'sma_{period}'] = df[column].rolling(window=period).mean()
    return df

def calculate_ema(df: pd.DataFrame, period: int = 20, column: str = 'close') -> pd.DataFrame:
    """
    计算指数移动平均线 (EMA)
    
    参数:
        df (pandas.DataFrame): 包含 OHLC 数据的 DataFrame
        period (int): 移动平均周期
        column (str): 用于计算的列名
        
    返回:
        pandas.DataFrame: 添加了 EMA 列的 DataFrame
    """
    df[f'ema_{period}'] = df[column].ewm(span=period, adjust=False).mean()
    return df

def calculate_rsi(df: pd.DataFrame, period: int = 14, column: str = 'close') -> pd.DataFrame:
    """
    计算相对强弱指数 (RSI)
    
    参数:
        df (pandas.DataFrame): 包含 OHLC 数据的 DataFrame
        period (int): RSI 周期
        column (str): 用于计算的列名
        
    返回:
        pandas.DataFrame: 添加了 RSI 列的 DataFrame
    """
    delta = df[column].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    rs = avg_gain / avg_loss
    df[f'rsi_{period}'] = 100 - (100 / (1 + rs))
    
    return df

def calculate_macd(df: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, 
                  signal_period: int = 9, column: str = 'close') -> pd.DataFrame:
    """
    计算移动平均收敛散度 (MACD)
    
    参数:
        df (pandas.DataFrame): 包含 OHLC 数据的 DataFrame
        fast_period (int): 快速 EMA 周期
        slow_period (int): 慢速 EMA 周期
        signal_period (int): 信号线周期
        column (str): 用于计算的列名
        
    返回:
        pandas.DataFrame: 添加了 MACD 相关列的 DataFrame
    """
    # 计算快速和慢速 EMA
    ema_fast = df[column].ewm(span=fast_period, adjust=False).mean()
    ema_slow = df[column].ewm(span=slow_period, adjust=False).mean()
    
    # 计算 MACD 线和信号线
    df['macd_line'] = ema_fast - ema_slow
    df['macd_signal'] = df['macd_line'].ewm(span=signal_period, adjust=False).mean()
    df['macd_histogram'] = df['macd_line'] - df['macd_signal']
    
    return df

def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0, 
                             column: str = 'close') -> pd.DataFrame:
    """
    计算布林带 (Bollinger Bands)
    
    参数:
        df (pandas.DataFrame): 包含 OHLC 数据的 DataFrame
        period (int): 移动平均周期
        std_dev (float): 标准差倍数
        column (str): 用于计算的列名
        
    返回:
        pandas.DataFrame: 添加了布林带相关列的 DataFrame
    """
    # 计算中轨 (SMA)
    df[f'bb_middle_{period}'] = df[column].rolling(window=period).mean()
    
    # 计算标准差
    rolling_std = df[column].rolling(window=period).std()
    
    # 计算上轨和下轨
    df[f'bb_upper_{period}'] = df[f'bb_middle_{period}'] + (rolling_std * std_dev)
    df[f'bb_lower_{period}'] = df[f'bb_middle_{period}'] - (rolling_std * std_dev)
    
    return df

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    计算平均真实范围 (ATR)
    
    参数:
        df (pandas.DataFrame): 包含 OHLC 数据的 DataFrame
        period (int): ATR 周期
        
    返回:
        pandas.DataFrame: 添加了 ATR 列的 DataFrame
    """
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    
    df[f'atr_{period}'] = true_range.rolling(window=period).mean()
    
    return df

def calculate_stochastic_oscillator(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> pd.DataFrame:
    """
    计算随机振荡器 (Stochastic Oscillator)
    
    参数:
        df (pandas.DataFrame): 包含 OHLC 数据的 DataFrame
        k_period (int): %K 周期
        d_period (int): %D 周期
        
    返回:
        pandas.DataFrame: 添加了随机振荡器相关列的 DataFrame
    """
    # 计算 %K
    low_min = df['low'].rolling(window=k_period).min()
    high_max = df['high'].rolling(window=k_period).max()
    
    df['stoch_k'] = 100 * ((df['close'] - low_min) / (high_max - low_min))
    
    # 计算 %D (K的移动平均)
    df['stoch_d'] = df['stoch_k'].rolling(window=d_period).mean()
    
    return df

def calculate_obv(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算能量潮 (On-Balance Volume, OBV)
    
    参数:
        df (pandas.DataFrame): 包含 OHLC 和成交量数据的 DataFrame
        
    返回:
        pandas.DataFrame: 添加了 OBV 列的 DataFrame
    """
    df['price_change'] = df['close'].diff()
    
    # 创建 OBV 列
    df['obv'] = 0
    
    # 第一个值设为成交量
    df.loc[0, 'obv'] = df.loc[0, 'volume']
    
    # 根据价格变化计算 OBV
    for i in range(1, len(df)):
        if df.loc[i, 'price_change'] > 0:
            df.loc[i, 'obv'] = df.loc[i-1, 'obv'] + df.loc[i, 'volume']
        elif df.loc[i, 'price_change'] < 0:
            df.loc[i, 'obv'] = df.loc[i-1, 'obv'] - df.loc[i, 'volume']
        else:
            df.loc[i, 'obv'] = df.loc[i-1, 'obv']
    
    # 删除临时列
    df.drop('price_change', axis=1, inplace=True)
    
    return df

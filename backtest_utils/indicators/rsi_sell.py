import pandas as pd
import numpy as np

def calculate_rsi_volume_sell_signal(df):
    """
    计算 RSI 超买和成交量增加时的卖出信号指标

    参数:
        df (pandas.DataFrame): 包含 OHLC 和成交量数据的 DataFrame

    返回:
        pandas.DataFrame: 添加了 'buy_signal' 和 'sell_signal' 列的 DataFrame
    """
    # 计算 RSI
    window_length = 14
    close = df['close']
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window_length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window_length).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    df['rsi'] = rsi

    # 计算成交量变化百分比
    df['volume_change'] = df['volume'].pct_change()

    # 初始化信号列
    df['buy_signal'] = 0
    df['sell_signal'] = 0

    # 生成卖出信号
    df.loc[(df['rsi'] > 70) & (df['volume_change'] > 0), 'sell_signal'] = 1

    return df

calculate_rsi_volume_sell_signal(df)
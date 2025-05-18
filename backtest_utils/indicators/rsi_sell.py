import pandas as pd
import numpy as np

def calculate_sell_signal_on_rise(df):
    """
    计算上涨0.1%就卖出的指标信号

    参数:
        df (pandas.DataFrame): 包含 OHLC 和成交量数据的 DataFrame

    返回:
        pandas.DataFrame: 添加了 'buy_signal' 和 'sell_signal' 列的 DataFrame
    """
    # 初始化信号列
    df['buy_signal'] = 0
    df['sell_signal'] = 0

    # 计算前一天的收盘价
    df['previous_close'] = df['close'].shift(1)

    # 计算上涨0.1%的条件
    df['price_increase'] = (df['close'] - df['previous_close']) / df['previous_close']

    # 生成卖出信号
    df.loc[df['price_increase'] >= 0.001, 'sell_signal'] = 1

    # 删除临时列
    df.drop(columns=['previous_close', 'price_increase'], inplace=True)

    return df

calculate_sell_signal_on_rise(df)
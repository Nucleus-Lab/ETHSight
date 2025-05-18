import pandas as pd
import numpy as np

def calculate_golden_cross_sell_signal(df):
    """
    计算黄金交叉卖出信号

    黄金交叉是指短期移动平均线（如 50 日均线）上穿长期移动平均线（如 200 日均线）。
    在这里，我们将生成一个卖出信号，当短期均线下穿长期均线时。

    参数:
        df (pandas.DataFrame): 包含 OHLC 和成交量数据的 DataFrame

    返回:
        pandas.DataFrame: 添加了 'buy_signal' 和 'sell_signal' 列的 DataFrame
    """
    # 计算短期和长期移动平均线
    short_window = 30
    long_window = 50

    df['short_mavg'] = df['close'].rolling(window=short_window, min_periods=1).mean()
    df['long_mavg'] = df['close'].rolling(window=long_window, min_periods=1).mean()

    # 初始化信号列
    df['buy_signal'] = 0
    df['sell_signal'] = 0

    # 生成卖出信号：短期均线下穿长期均线
    df['sell_signal'] = np.where((df['short_mavg'].shift(1) > df['long_mavg'].shift(1)) & 
                                 (df['short_mavg'] <= df['long_mavg']), 1, 0)

    # 删除临时计算列
    df.drop(['short_mavg', 'long_mavg'], axis=1, inplace=True)

    return df

calculate_golden_cross_sell_signal(df)
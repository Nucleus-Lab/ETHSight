import pandas as pd
import numpy as np

def calculate_buy_on_drop_signal(df):
    """
    计算下跌0.1%就买入的指标信号

    参数:
        df (pandas.DataFrame): 包含 open, high, low, close, volume, datetime 列的 DataFrame

    返回:
        pandas.DataFrame: 添加了 'buy_signal' 和 'sell_signal' 列的 DataFrame
    """
    # 初始化信号列
    df['buy_signal'] = 0
    df['sell_signal'] = 0

    # 计算前一日的收盘价
    df['previous_close'] = df['close'].shift(1)

    # 计算价格下跌的百分比
    df['price_drop'] = (df['close'] - df['previous_close']) / df['previous_close']

    # 生成买入信号：当价格下跌超过 0.1% 时
    df.loc[df['price_drop'] <= -0.001, 'buy_signal'] = 1

    # 删除临时列
    df.drop(columns=['previous_close', 'price_drop'], inplace=True)

    return df

calculate_buy_on_drop_signal(df)
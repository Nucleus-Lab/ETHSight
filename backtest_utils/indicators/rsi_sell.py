import pandas as pd
import numpy as np

def rsi_sell(df):
    """
    生成测试用的卖出信号

    参数:
        df (pandas.DataFrame): 包含 OHLC 和成交量数据的 DataFrame

    返回:
        pandas.DataFrame: 添加了买入和卖出信号列的 DataFrame
    """
    # 初始化买入和卖出信号列
    df['buy_signal'] = 0
    df['sell_signal'] = 0
    
    # 每 10 个数据点生成一个卖出信号
    for i in range(0, len(df), 10):
        if i < len(df):
            df.loc[df.index[i], 'sell_signal'] = 1
    
    # 确保至少有一个卖出信号
    if df['sell_signal'].sum() == 0 and len(df) > 0:
        # 如果没有生成信号，在第一个和最后一个数据点生成信号
        df.loc[df.index[0], 'sell_signal'] = 1
        if len(df) > 1:
            df.loc[df.index[-1], 'sell_signal'] = 1
    
    # 每个卖出信号后的第 5 个点生成买入信号（如果存在）
    sell_indices = df.index[df['sell_signal'] == 1].tolist()
    for idx in sell_indices:
        pos = df.index.get_loc(idx)
        if pos + 5 < len(df):
            df.loc[df.index[pos + 5], 'buy_signal'] = 1
    
    # 添加一些指标列供显示
    df['rsi'] = df['close'].rolling(window=14).mean()
    df['rsi_signal'] = df['rsi'].rolling(window=3).mean()
    
    print(f"\n生成了 {df['buy_signal'].sum()} 个买入信号")
    print(f"生成了 {df['sell_signal'].sum()} 个卖出信号\n")
    
    return df

# 执行函数以确保信号生成
rsi_sell(df)
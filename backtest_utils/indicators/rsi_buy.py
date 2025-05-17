import pandas as pd
import numpy as np

def rsi_buy(df):
    """
    生成测试用的买入信号

    参数:
        df (pandas.DataFrame): 包含 OHLC 和成交量数据的 DataFrame

    返回:
        pandas.DataFrame: 添加了买入和卖出信号列的 DataFrame
    """
    # 初始化买入和卖出信号列
    df['buy_signal'] = 0
    df['sell_signal'] = 0
    
    # 每 10 个数据点生成一个买入信号
    for i in range(0, len(df), 10):
        if i < len(df):
            df.loc[df.index[i], 'buy_signal'] = 1
    
    # 确保至少有一个买入信号
    if df['buy_signal'].sum() == 0 and len(df) > 0:
        # 如果没有生成信号，在第一个和最后一个数据点生成信号
        df.loc[df.index[0], 'buy_signal'] = 1
        if len(df) > 1:
            df.loc[df.index[-1], 'buy_signal'] = 1
    
    # 每个买入信号后的第 5 个点生成卖出信号（如果存在）
    buy_indices = df.index[df['buy_signal'] == 1].tolist()
    for idx in buy_indices:
        pos = df.index.get_loc(idx)
        if pos + 5 < len(df):
            df.loc[df.index[pos + 5], 'sell_signal'] = 1
    
    # 添加一些指标列供显示
    df['test_indicator'] = df['close'].rolling(window=3).mean()
    
    print(f"\n生成了 {df['buy_signal'].sum()} 个买入信号")
    print(f"生成了 {df['sell_signal'].sum()} 个卖出信号\n")
    
    return df

# 调用函数处理数据
df = rsi_buy(df)
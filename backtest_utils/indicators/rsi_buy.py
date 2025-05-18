import pandas as pd
import numpy as np

def calculate_rsi_buy_signal(df):
    """
    计算RSI超卖和价格下跌时的买入信号指标
    
    参数:
        df (pandas.DataFrame): 包含 OHLC 和成交量数据的 DataFrame
        
    返回:
        pandas.DataFrame: 添加了买入信号和卖出信号列的 DataFrame
    """
    # 初始化信号列
    df['buy_signal'] = 0
    df['sell_signal'] = 0
    
    # 计算RSI
    window_length = 14
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window_length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window_length).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 计算前一日的收盘价
    df['previous_close'] = df['close'].shift(1)
    
    # 计算价格下跌的百分比
    df['price_drop'] = (df['close'] - df['previous_close']) / df['previous_close']
    
    # 打印价格下跌的统计信息
    drop_count = (df['price_drop'] <= -0.001).sum()
    print(f"价格下跌超过0.1%的点数: {drop_count} (占总数的 {drop_count/len(df)*100:.2f}%)")
    
    # 生成买入信号：当RSI < 30且价格下跌超过0.1%时
    df.loc[(df['rsi'] < 30) & (df['price_drop'] <= -0.001), 'buy_signal'] = 1
    
    # 确保信号列是整数类型
    df['buy_signal'] = df['buy_signal'].astype(int)
    df['sell_signal'] = df['sell_signal'].astype(int)
    
    # 打印买入信号统计
    buy_count = df['buy_signal'].sum()
    print(f"生成的买入信号数量: {buy_count} (占总数的 {buy_count/len(df)*100:.2f}%)")
    
    # 删除临时列
    df.drop(columns=['previous_close', 'price_drop'], inplace=True)
    
    return df

calculate_rsi_buy_signal(df)
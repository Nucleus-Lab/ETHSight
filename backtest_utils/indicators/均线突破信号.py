"""
均线突破信号

描述:
创建一个指标，当价格突破20日均线且成交量增加50%时发出买入信号

生成时间: 2025-05-17 19:27:00
"""

import pandas as pd
import numpy as np

import pandas as pd
import numpy as np

def breakout_ma20_volume_signal(df):
    """
    计算价格突破20日均线且成交量增加50%的买入信号指标

    指标说明:
        当收盘价上穿20日简单移动平均线（MA20），且当日成交量较前一日增加至少50%时，发出买入信号（1），否则为0。
        该指标用于捕捉价格强势突破并伴随放量的交易机会。

    参数:
        df (pandas.DataFrame): 包含 OHLC 和成交量等信息的 DataFrame，需包含以下列:
            ['timestamp','open','high','low','close','volume','datetime',
             'base_token_address','base_token_name','base_token_symbol',
             'quote_token_address','quote_token_name','quote_token_symbol']

    返回:
        pandas.DataFrame: 在原始 DataFrame 基础上新增 'breakout_ma20_vol_signal' 列，表示买入信号（1为信号，0为无信号）
    """
    df = df.copy()
    # 计算20日简单移动平均线
    df['ma20'] = df['close'].rolling(window=20, min_periods=1).mean()
    # 计算成交量前一日
    df['volume_prev'] = df['volume'].shift(1)
    # 计算收盘价前一日
    df['close_prev'] = df['close'].shift(1)
    # 计算MA20前一日
    df['ma20_prev'] = df['ma20'].shift(1)

    # 条件1: 收盘价从下向上突破MA20
    breakout = (df['close_prev'] <= df['ma20_prev']) & (df['close'] > df['ma20'])
    # 条件2: 成交量较前一日增加至少50%
    vol_increase = (df['volume'] >= 1.5 * df['volume_prev'])

    # 综合信号
    df['breakout_ma20_vol_signal'] = np.where(breakout & vol_increase, 1, 0)

    # 清理临时列
    df.drop(['ma20', 'volume_prev', 'close_prev', 'ma20_prev'], axis=1, inplace=True)

    return df

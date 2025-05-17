import requests
import pandas as pd

pair_address = '0x60594a405d53811d3bc4766596efd80fd545a270'  # 示例: WETH/USDC on Uniswap V3

'''
TODO
用mcp_server_ohlcv里的get_ohlcv_data获取 OHLCV
再解析为df
'''

# JH's function
def breakout_ma20_volume_spike_signal(df):
        """
        计算价格突破20日均线且成交量增加50%的买入信号指标
        指标说明:
            当收盘价从下方向上突破20日移动均线 即昨日收盘价低于昨日20日均线 今日收盘价高于今日20日均线
            且今日成交量较昨日增加至少50%时，发出买入信号 信号值为1 否则为0。
        参数:
            df (pandas.DataFrame): 包含 OHLC 和成交量等数据的 DataFrame。
                必须包含 'close' 和 'volume' 列。
        返回：
            pandas.DataFrame: 添加了 'breakout_ma20_vol_spike_signal' 指标列的 DataFrame。
        """
        df = df.copy()
        # 计算20日移动均线
        df['ma20'] = df['close'].rolling(window=20, min_periods=1).mean()
        # 前一日收盘价和20日均线
        df['close_prev'] = df['close'].shift(1)
        df['ma20_prev'] = df['ma20'].shift(1)
        # 前一日成交量
        df['volume_prev'] = df['volume'].shift(1)
        # 条件1: 收盘价从下方突破20日均线
        price_breakout = (df['close_prev'] < df['ma20_prev']) & (df['close'] > df['ma20'])
        # 条件2: 成交量较昨日增加50%
        volume_spike = (df['volume'] >= 1.5 * df['volume_prev'])
        # 买入信号
        df['breakout_ma20_vol_spike_signal'] = np.where(price_breakout & volume_spike, 1, 0)
        # 清理临时列
        df.drop(['ma20', 'close_prev', 'ma20_prev', 'volume_prev'], axis=1, inplace=True)
        return df

df_signal = breakout_ma20_volume_spike_signal(df)

if df_signal['breakout_ma20_vol_spike_signal'].iloc[-1] == 1:
    print("✅ Buy signal detected!")
else:
    print("❌ No buy signal.")


'''
TODO
调用trade.py的逻辑进行交易
'''
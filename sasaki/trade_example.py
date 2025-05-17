import os
import pandas as pd
import numpy as np
from uniswap_swap import UniswapTrader, Network
from mcp_server_ohlcv import get_ohlcv_data
from dotenv import load_dotenv
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 网络设置
NETWORK = Network.ARBITRUM  # 可以切换为 Network.MAINNET

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

def get_ohlcv_dataframe(pool_address, network="eth", timeframe="day", limit=100):
    """
    获取OHLCV数据并转换为DataFrame
    
    Args:
        pool_address (str): 交易池地址
        network (str): 区块链网络
        timeframe (str): 时间周期
        limit (int): 数据点数量
        
    Returns:
        pandas.DataFrame: OHLCV数据的DataFrame
    """
    try:
        # 调用MCP服务器获取OHLCV数据
        response = get_ohlcv_data(
            pool_address=pool_address,
            network=network,
            timeframe=timeframe,
            limit=limit
        )
        
        # 检查响应
        if 'data' not in response or 'attributes' not in response['data']:
            logger.error(f"API响应格式错误: {response}")
            return None
        
        # 提取OHLCV数据
        ohlcv_data = response['data']['attributes']['ohlcv_list']
        
        # 创建DataFrame
        df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # 转换时间戳为日期时间
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        
        # 确保数值列是浮点型
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        logger.info(f"成功获取{len(df)}条OHLCV数据")
        return df
    
    except Exception as e:
        logger.error(f"获取OHLCV数据失败: {str(e)}")
        return None

def judge_and_trade(pool_address, token_address, eth_amount=0.01, network=NETWORK):
    """
    判断交易信号并执行交易
    
    Args:
        pool_address (str): 交易池地址
        token_address (str): 代币合约地址
        eth_amount (float): 交易ETH数量
        
    Returns:
        bool: 是否执行了交易
    """
    try:
        # 获取OHLCV数据
        df = get_ohlcv_dataframe(pool_address)
        if df is None or len(df) < 20:
            logger.error("获取数据失败或数据点不足")
            return False
        
        # 计算交易信号
        df_signal = breakout_ma20_volume_spike_signal(df)
        
        # 检查最新的信号
        latest_signal = df_signal['breakout_ma20_vol_spike_signal'].iloc[-1]
        
        if latest_signal == 1:
            logger.info("✅ 检测到买入信号!")
            
            # 初始化交易实例
            trader = UniswapTrader(network=network)
            
            # 获取ETH余额
            eth_balance = trader.get_token_balance("eth")
            logger.info(f"当前ETH余额: {eth_balance}")
            
            # 检查余额是否足够
            if eth_balance < eth_amount:
                logger.error(f"ETH余额不足: {eth_balance} < {eth_amount}")
                return False
            
            # 执行交易
            tx_hash = trader.swap_eth_for_token(token_address, eth_amount)
            
            if tx_hash:
                logger.info(f"交易成功执行! 交易哈希: {tx_hash}")
                return True
            else:
                logger.error("交易执行失败")
                return False
        else:
            logger.info("❌ 未检测到买入信号")
            return False
    
    except Exception as e:
        logger.error(f"判断交易信号时发生错误: {str(e)}")
        return False

# 示例用法
if __name__ == "__main__":
    # 根据网络选择交易池和代币
    if NETWORK == Network.MAINNET:
        # 以太坊主网 Uniswap V3上的WETH/USDC交易池
        pool_address = '0x60594a405d53811d3bc4766596efd80fd545a270'
    else:  # Arbitrum
        # Arbitrum上的WETH/USDC交易池 (Uniswap V3)
        pool_address = '0xc31e54c7a869b9fcbecc14363cf510d1c41fa443'
    
    # 初始化交易实例以获取代币地址
    trader = UniswapTrader(network=NETWORK)
    # 获取当前网络的USDC地址
    token_address = trader.token_addresses["USDC"]
    
    # 判断信号并交易
    result = judge_and_trade(pool_address, token_address, eth_amount=0.01)
    
    if result:
        print("✅ 交易已成功执行!")
    else:
        print("❌ 未执行交易")

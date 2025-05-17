import os
from uniswap_swap import UniswapTrader, Network
from dotenv import load_dotenv
import logging
import argparse

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 常用代币符号映射
TOKEN_SYMBOLS = {
    "eth": "WETH",  # ETH会自动处理为WETH
    "weth": "WETH",
    "usdc": "USDC",
    "dai": "DAI",
    "usdt": "USDT",
    "wbtc": "WBTC"
}

def get_token_address(trader, token_symbol):
    """获取代币地址，支持常用代币符号或直接使用地址"""
    if token_symbol.lower() in TOKEN_SYMBOLS:
        symbol = TOKEN_SYMBOLS[token_symbol.lower()]
        if symbol in trader.token_addresses:
            return trader.token_addresses[symbol]
        else:
            raise ValueError(f"不支持的代币符号: {token_symbol}")
    elif token_symbol.startswith("0x"):
        # 假设是代币地址
        return token_symbol
    else:
        raise ValueError(f"无效的代币符号或地址: {token_symbol}")

def swap_tokens(from_token, to_token, amount, network=Network.ARBITRUM, slippage=0.5, version=3):
    """执行代币交换
    
    Args:
        from_token (str): 源代币符号或地址
        to_token (str): 目标代币符号或地址
        amount (float): 交换数量
        network (Network): 网络类型
        slippage (float): 滑点百分比
        version (int): Uniswap版本
    """
    try:
        # 初始化交易实例
        trader = UniswapTrader(network=network)
        
        # 获取代币地址
        from_address = "eth" if from_token.lower() == "eth" else get_token_address(trader, from_token)
        to_address = get_token_address(trader, to_token)
        
        # 获取代币符号（用于显示）
        from_symbol = from_token.upper() if from_token.lower() == "eth" else from_token.upper()
        to_symbol = to_token.upper()
        
        logger.info(f"准备交换: {amount} {from_symbol} -> {to_symbol}")
        logger.info(f"网络: {network.value}, Uniswap版本: v{version}, 滑点: {slippage}%")
        
        # 检查余额
        if from_token.lower() == "eth":
            balance = trader.get_token_balance("eth")
            logger.info(f"当前ETH余额: {balance}")
            
            if balance < amount:
                logger.error(f"ETH余额不足: {balance} < {amount}")
                return False
            
            # 使用ETH购买代币
            tx_hash = trader.swap_eth_for_token(to_address, amount, slippage=slippage, version=version)
        else:
            # 获取代币余额
            balance = trader.get_token_balance(from_address)
            logger.info(f"当前{from_symbol}余额: {balance}")
            
            if balance < amount:
                logger.error(f"{from_symbol}余额不足: {balance} < {amount}")
                return False
            
            # 如果目标是ETH
            if to_token.lower() == "eth" or to_token.lower() == "weth":
                # 将代币卖出换成ETH
                tx_hash = trader.swap_token_for_eth(from_address, amount, slippage=slippage, version=version)
            else:
                # 代币到代币的交换（目前uniswap-python库不直接支持，需要两步操作）
                logger.error("代币到代币的直接交换暂不支持，请先换成ETH再换成目标代币")
                return False
        
        if tx_hash:
            logger.info(f"交易成功执行! 交易哈希: {tx_hash}")
            return True
        else:
            logger.error("交易执行失败")
            return False
            
    except Exception as e:
        logger.error(f"交换代币时发生错误: {str(e)}")
        return False

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="简单的代币交换工具")
    parser.add_argument("--from", dest="from_token", required=True, help="源代币符号或地址 (例如: eth, usdc, 0x...)")
    parser.add_argument("--to", dest="to_token", required=True, help="目标代币符号或地址 (例如: usdc, eth, 0x...)")
    parser.add_argument("--amount", type=float, required=True, help="交换数量")
    parser.add_argument("--network", choices=["mainnet", "arbitrum"], default="arbitrum", help="网络 (默认: arbitrum)")
    parser.add_argument("--slippage", type=float, default=0.5, help="滑点百分比 (默认: 0.5)")
    parser.add_argument("--version", type=int, choices=[2, 3], default=3, help="Uniswap版本 (默认: 3)")
    
    args = parser.parse_args()
    
    # 设置网络
    network = Network.MAINNET if args.network == "mainnet" else Network.ARBITRUM
    
    # 执行交换
    result = swap_tokens(
        args.from_token, 
        args.to_token, 
        args.amount,
        network=network,
        slippage=args.slippage,
        version=args.version
    )
    
    if result:
        print(f"✅ 成功交换 {args.amount} {args.from_token.upper()} 到 {args.to_token.upper()}")
    else:
        print(f"❌ 交换失败")

if __name__ == "__main__":
    main()

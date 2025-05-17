#!/usr/bin/env python3
"""
直接代币交换脚本 - 在Arbitrum网络上执行简单的代币交换操作
"""

import os
import sys
import argparse
from web3 import Web3
from uniswap import Uniswap
from dotenv import load_dotenv
import logging
from uniswap.constants import ETH_ADDRESS

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# Arbitrum网络配置
ARBITRUM_RPC = "https://arbitrum-mainnet.infura.io/v3/{}"
ARBITRUM_CHAIN_ID = 42161

# Arbitrum上常用代币地址
TOKEN_ADDRESSES = {
    "weth": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
    "eth": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",  # 使用WETH地址
    "usdc": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
    "usdt": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
    "dai": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
    "wbtc": "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f"
}

def get_token_address(token_symbol):
    """获取代币地址"""
    token_symbol = token_symbol.lower()
    
    if token_symbol in TOKEN_ADDRESSES:
        return TOKEN_ADDRESSES[token_symbol]
    elif token_symbol.startswith("0x"):
        # 假设是代币地址
        return Web3.to_checksum_address(token_symbol)
    else:
        raise ValueError(f"未知的代币符号: {token_symbol}")

def setup_uniswap():
    """设置Uniswap客户端"""
    # 从环境变量获取配置
    infura_key = os.getenv("INFURA_KEY")
    wallet_address = os.getenv("WALLET_ADDRESS")
    private_key = os.getenv("PRIVATE_KEY")
    
    if not all([infura_key, wallet_address, private_key]):
        logger.error("环境变量未设置完全。请确保设置了INFURA_KEY, WALLET_ADDRESS和PRIVATE_KEY")
        sys.exit(1)
    
    # 设置RPC URL
    provider_url = ARBITRUM_RPC.format(infura_key)
    
    # 初始化Web3
    web3 = Web3(Web3.HTTPProvider(provider_url))
    
    # 检查连接
    if not web3.is_connected():
        logger.error(f"无法连接到Arbitrum网络: {provider_url}")
        sys.exit(1)
    
    logger.info(f"成功连接到Arbitrum网络，当前区块: {web3.eth.block_number}")
    
    # 初始化Uniswap客户端
    try:
        # 尝试使用Uniswap V3
        uniswap = Uniswap(
            address=wallet_address,
            private_key=private_key,
            version=3,
            provider=provider_url
        )
        logger.info("使用Uniswap V3")
    except Exception as e:
        logger.warning(f"初始化Uniswap V3失败: {e}，尝试使用V2")
        # 如果V3初始化失败，尝试使用V2
        uniswap = Uniswap(
            address=wallet_address,
            private_key=private_key,
            version=2,
            provider=provider_url
        )
        logger.info("使用Uniswap V2")
    
    return uniswap, web3, wallet_address

def eth_to_token(uniswap, web3, wallet_address, token_address, amount, slippage=0.5):
    """使用ETH购买代币"""
    # 检查ETH余额
    eth_balance = web3.eth.get_balance(wallet_address)
    eth_balance_human = web3.from_wei(eth_balance, 'ether')
    
    logger.info(f"当前ETH余额: {eth_balance_human}")
    
    # 将ETH数量转换为Wei
    amount_wei = web3.to_wei(amount, 'ether')
    
    if eth_balance < amount_wei:
        logger.error(f"ETH余额不足: {eth_balance_human} < {amount}")
        return None
    
    try:
        # 执行交易
        logger.info(f"使用 {amount} ETH 购买代币...")
        
        # 获取当前gas价格
        gas_price = web3.eth.gas_price
        logger.info(f"当前Gas价格: {web3.from_wei(gas_price, 'gwei')} Gwei")
        
        
        # 执行交换
        # 在eth_to_token函数中
        tx_hash = uniswap.make_trade(
            ETH_ADDRESS,
            token_address,
            amount_wei,  # 已经是wei单位，不需要再乘以10^18
            slippage=slippage/100,
            fee=500
        )
        
        logger.info(f"交易已提交，交易哈希: {tx_hash.hex()}")
        
        # 等待交易确认
        logger.info("等待交易确认...")
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        
        if receipt['status'] == 1:
            logger.info(f"交易成功! Gas使用: {receipt['gasUsed']}")
            return tx_hash.hex()
        else:
            logger.error(f"交易失败! Gas使用: {receipt['gasUsed']}")
            return None
            
    except Exception as e:
        logger.error(f"交易失败: {str(e)}")
        return None

def token_to_eth(uniswap, web3, wallet_address, token_address, amount, slippage=0.5):
    """将代币卖出换成ETH"""
    try:
        # 获取代币信息
        # 完整的ERC20 ABI，包含allowance和approve函数
        ERC20_ABI = [
            {
                "constant": True,
                "inputs": [],
                "name": "name",
                "outputs": [{"name": "", "type": "string"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}],
                "name": "approve",
                "outputs": [{"name": "", "type": "bool"}],
                "payable": False,
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "totalSupply",
                "outputs": [{"name": "", "type": "uint256"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [{"name": "_from", "type": "address"}, {"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}],
                "name": "transferFrom",
                "outputs": [{"name": "", "type": "bool"}],
                "payable": False,
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "symbol",
                "outputs": [{"name": "", "type": "string"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "payable": False,
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}],
                "name": "allowance",
                "outputs": [{"name": "", "type": "uint256"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "_from", "type": "address"},
                    {"indexed": True, "name": "_to", "type": "address"},
                    {"indexed": False, "name": "_value", "type": "uint256"}
                ],
                "name": "Transfer",
                "type": "event"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "_owner", "type": "address"},
                    {"indexed": True, "name": "_spender", "type": "address"},
                    {"indexed": False, "name": "_value", "type": "uint256"}
                ],
                "name": "Approval",
                "type": "event"
            }
        ]
        
        token_contract = web3.eth.contract(
            address=token_address,
            abi=ERC20_ABI
        )
        
        # 获取代币余额和精度
        token_decimals = token_contract.functions.decimals().call()
        token_balance = token_contract.functions.balanceOf(wallet_address).call()
        token_symbol = token_contract.functions.symbol().call()
        
        # 将代币数量转换为最小单位
        token_amount_wei = int(amount * (10 ** token_decimals))
        token_balance_human = token_balance / (10 ** token_decimals)
        
        logger.info(f"当前{token_symbol}余额: {token_balance_human}")
        
        if token_balance < token_amount_wei:
            logger.error(f"{token_symbol}余额不足: {token_balance_human} < {amount}")
            return None
        
        # 检查授权
        # 获取Uniswap路由器地址
        router_address = uniswap.address
        
        # 检查代币授权
        allowance = token_contract.functions.allowance(wallet_address, router_address).call()
        if allowance < token_amount_wei:
            logger.info(f"需要授权{token_symbol}给Uniswap...")
            
            # 构建授权交易
            approve_tx = token_contract.functions.approve(
                router_address,
                2**256 - 1  # 最大值
            ).build_transaction({
                'from': wallet_address,
                'gas': 100000,
                'gasPrice': web3.eth.gas_price,
                'nonce': web3.eth.get_transaction_count(wallet_address),
            })
            
            # 签名并发送交易
            signed_tx = web3.eth.account.sign_transaction(approve_tx, os.getenv("PRIVATE_KEY"))
            tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            logger.info(f"授权交易已提交: {tx_hash.hex()}")
            
            # 等待授权确认
            logger.info("等待授权确认...")
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            
            if receipt['status'] == 1:
                logger.info("授权成功!")
            else:
                logger.error("授权失败!")
                return None
        
        # 执行交易
        logger.info(f"卖出 {amount} {token_symbol} 换取ETH...")
        
        # 获取当前gas价格
        gas_price = web3.eth.gas_price
        logger.info(f"当前Gas价格: {web3.from_wei(gas_price, 'gwei')} Gwei")
        
        # 执行交换
        tx_hash = uniswap.make_trade(
            token_address,            # 输入代币
            TOKEN_ADDRESSES["weth"],  # 输出代币 (WETH)
            token_amount_wei,         # 输入金额
            slippage=slippage/100,    # 滑点 (转换为小数)
            fee=500                   # 费率 (0.05%)
        )
        logger.info(f"交易已提交，交易哈希: {tx_hash.hex()}")
        
        # 等待交易确认
        logger.info("等待交易确认...")
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        
        if receipt['status'] == 1:
            logger.info(f"交易成功! Gas使用: {receipt['gasUsed']}")
            return tx_hash.hex()
        else:
            logger.error(f"交易失败! Gas使用: {receipt['gasUsed']}")
            return None
            
    except Exception as e:
        logger.error(f"交易失败: {str(e)}")
        return None

def main():
    parser = argparse.ArgumentParser(description="在Arbitrum上执行代币交换")
    parser.add_argument("--from", dest="from_token", required=True, help="源代币符号或地址 (例如: eth, usdc, 0x...)")
    parser.add_argument("--to", dest="to_token", required=True, help="目标代币符号或地址 (例如: usdc, eth, 0x...)")
    parser.add_argument("--amount", type=float, required=True, help="交换数量")
    parser.add_argument("--slippage", type=float, default=0.5, help="滑点百分比 (默认: 0.5)")
    
    args = parser.parse_args()
    
    try:
        # 设置Uniswap
        uniswap, web3, wallet_address = setup_uniswap()
        
        # 获取代币地址
        from_address = get_token_address(args.from_token)
        to_address = get_token_address(args.to_token)
        
        # 执行交换
        if args.from_token.lower() == "eth":
            # ETH到代币
            tx_hash = eth_to_token(uniswap, web3, wallet_address, to_address, args.amount, args.slippage)
        elif args.to_token.lower() == "eth":
            # 代币到ETH
            tx_hash = token_to_eth(uniswap, web3, wallet_address, from_address, args.amount, args.slippage)
        else:
            logger.error("目前只支持ETH与代币之间的直接交换")
            logger.info("提示: 如需交换代币到代币，请先将代币换成ETH，再将ETH换成目标代币")
            sys.exit(1)
        
        if tx_hash:
            print(f"✅ 交易成功! 交易哈希: {tx_hash}")
            print(f"可在 https://arbiscan.io/tx/{tx_hash} 查看交易详情")
        else:
            print("❌ 交易失败!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Arbitrum网络上的Uniswap代币交换脚本
支持ETH到代币和代币到ETH的交换，具有动态费率探测功能
"""

import os
import sys
import time
import json
import logging
import argparse
from decimal import Decimal
from dotenv import load_dotenv
from web3 import Web3
from uniswap import Uniswap

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('arbitrum_swap.log')
    ]
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 网络配置
NETWORKS = {
    "arbitrum": {
        "rpc": os.getenv("ARBITRUM_RPC_URL", "https://arb1.arbitrum.io/rpc"),
        "chain_id": 42161,
        "explorer": "https://arbiscan.io/tx/"
    },
    "ethereum": {
        "rpc": os.getenv("ETH_RPC_URL", "https://mainnet.infura.io/v3/"),
        "chain_id": 1,
        "explorer": "https://etherscan.io/tx/"
    }
}

# 代币地址配置
TOKEN_ADDRESSES = {
    "arbitrum": {
        "weth": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
        "usdc": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
        "usdt": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
        "dai": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
        "wbtc": "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f"
    },
    "ethereum": {
        "weth": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "usdc": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "usdt": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "dai": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "wbtc": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599"
    }
}

# ERC20代币ABI
ERC20_ABI = json.loads('''[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_from","type":"address"},{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transferFrom","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"anonymous":false,"inputs":[{"indexed":true,"name":"_from","type":"address"},{"indexed":true,"name":"_to","type":"address"},{"indexed":false,"name":"_value","type":"uint256"}],"name":"Transfer","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"_owner","type":"address"},{"indexed":true,"name":"_spender","type":"address"},{"indexed":false,"name":"_value","type":"uint256"}],"name":"Approval","type":"event"}]''')

class ArbitrumSwapper:
    def __init__(self, network="arbitrum"):
        """
        初始化交换器
        
        Args:
            network: 网络名称 ("arbitrum" 或 "ethereum")
        """
        self.network = network
        self.network_config = NETWORKS[network]
        self.token_addresses = TOKEN_ADDRESSES[network]
        
        # 连接到网络
        self.web3 = Web3(Web3.HTTPProvider(self.network_config["rpc"]))
        if not self.web3.is_connected():
            raise ConnectionError(f"无法连接到{network}网络")
        
        # 获取钱包信息
        self.wallet_address = os.getenv("WALLET_ADDRESS")
        self.private_key = os.getenv("PRIVATE_KEY")
        
        if not self.wallet_address or not self.private_key:
            raise ValueError("请在.env文件中设置WALLET_ADDRESS和PRIVATE_KEY")
        
        # 确保地址格式正确
        self.wallet_address = Web3.to_checksum_address(self.wallet_address)
        
        # 初始化Uniswap
        self.uniswap = Uniswap(
            version=3,
            provider=self.web3,
            address=self.wallet_address,
            private_key=self.private_key
        )
        
        logger.info(f"已连接到{network}网络")
        logger.info(f"钱包地址: {self.wallet_address}")
        logger.info(f"ETH余额: {self.web3.from_wei(self.web3.eth.get_balance(self.wallet_address), 'ether')} ETH")
    
    def get_token_info(self, token_address):
        """
        获取代币信息
        
        Args:
            token_address: 代币合约地址
            
        Returns:
            (symbol, decimals): 代币符号和小数位数
        """
        token_contract = self.web3.eth.contract(address=token_address, abi=ERC20_ABI)
        try:
            symbol = token_contract.functions.symbol().call()
            decimals = token_contract.functions.decimals().call()
            return symbol, decimals
        except Exception as e:
            logger.error(f"获取代币信息失败: {str(e)}")
            return "UNKNOWN", 18
    
    def get_token_balance(self, token_address):
        """
        获取代币余额
        
        Args:
            token_address: 代币合约地址
            
        Returns:
            (balance_wei, balance, symbol): 代币余额（wei）、代币余额（可读）和代币符号
        """
        token_contract = self.web3.eth.contract(address=token_address, abi=ERC20_ABI)
        symbol, decimals = self.get_token_info(token_address)
        balance_wei = token_contract.functions.balanceOf(self.wallet_address).call()
        balance = balance_wei / (10 ** decimals)
        return balance_wei, balance, symbol
    
    def approve_token(self, token_address, amount=None):
        """
        授权代币给Uniswap
        
        Args:
            token_address: 代币合约地址
            amount: 授权金额，默认为最大值
            
        Returns:
            bool: 授权是否成功
        """
        token_contract = self.web3.eth.contract(address=token_address, abi=ERC20_ABI)
        symbol, _ = self.get_token_info(token_address)
        
        # 如果未指定金额，则使用最大值
        if amount is None:
            amount = 2**256 - 1
        
        try:
            logger.info(f"授权 {symbol} 给 Uniswap...")
            
            # 获取当前gas价格并适当提高
            gas_price = int(self.web3.eth.gas_price * 1.1)  # 增加10%
            
            approve_tx = token_contract.functions.approve(
                self.uniswap.address,
                amount
            ).build_transaction({
                'from': self.wallet_address,
                'gas': 100000,
                'gasPrice': gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.wallet_address),
            })
            
            signed_tx = self.web3.eth.account.sign_transaction(approve_tx, self.private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            logger.info(f"授权交易已提交，交易哈希: {tx_hash.hex()}")
            
            # 等待交易确认
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            
            if receipt['status'] == 1:
                logger.info(f"授权成功! Gas使用: {receipt['gasUsed']}")
                return True
            else:
                logger.error(f"授权失败! Gas使用: {receipt['gasUsed']}")
                return False
                
        except Exception as e:
            logger.error(f"授权失败: {str(e)}")
            return False
    
    def find_best_fee_rate(self, input_token, output_token, amount_wei):
        """
        找到最佳费率
        
        Args:
            input_token: 输入代币地址
            output_token: 输出代币地址
            amount_wei: 输入金额（wei）
            
        Returns:
            (fee, price): 最佳费率和预期价格，如果没有找到则返回(None, None)
        """
        # 尝试不同的费率
        fee_rates = [500, 3000, 10000]  # 0.05%, 0.3%, 1%
        
        for fee in fee_rates:
            try:
                logger.info(f"尝试费率: {fee} ({fee/10000}%)")
                price = self.uniswap.get_price_input(
                    input_token,
                    output_token,
                    amount_wei,
                    fee=fee
                )
                
                in_symbol, in_decimals = self.get_token_info(input_token)
                out_symbol, out_decimals = self.get_token_info(output_token)
                
                in_amount = amount_wei / (10 ** in_decimals)
                out_amount = price / (10 ** out_decimals)
                
                logger.info(f"费率 {fee} 可用: {in_amount} {in_symbol} -> {out_amount} {out_symbol}")
                return fee, price
            except Exception as e:
                logger.warning(f"费率 {fee} 不可用: {str(e)}")
        
        logger.error("找不到可用的费率")
        return None, None
    
    def eth_to_token(self, token_address, eth_amount, slippage=1.0):
        """
        将ETH交换为代币
        
        Args:
            token_address: 代币合约地址
            eth_amount: 要交换的ETH数量
            slippage: 滑点百分比
            
        Returns:
            交易哈希或None（如果失败）
        """
        try:
            # 获取代币信息
            token_symbol, token_decimals = self.get_token_info(token_address)
            
            # 计算ETH数量（以wei为单位）
            eth_amount_wei = self.web3.to_wei(eth_amount, 'ether')
            
            # 检查ETH余额
            eth_balance = self.web3.eth.get_balance(self.wallet_address)
            if eth_balance < eth_amount_wei:
                logger.error(f"ETH余额不足: 需要 {eth_amount} ETH，但只有 {self.web3.from_wei(eth_balance, 'ether')} ETH")
                return None
            
            logger.info(f"买入 {token_symbol} 使用 {eth_amount} ETH...")
            
            # 找到最佳费率
            fee, expected_tokens = self.find_best_fee_rate(
                self.token_addresses["weth"],
                token_address,
                eth_amount_wei
            )
            
            if fee is None:
                logger.error("无法找到可用的交易池")
                return None
            
            # 获取当前gas价格并适当提高
            gas_price = int(self.web3.eth.gas_price * 1.1)  # 增加10%
            logger.info(f"当前Gas价格: {self.web3.from_wei(gas_price, 'gwei')} Gwei")
            
            # 执行交换
            tx_hash = self.uniswap.make_trade(
                self.token_addresses["weth"],  # 输入代币 (WETH)
                token_address,                # 输出代币
                eth_amount_wei,               # 输入金额
                slippage=slippage/100,        # 滑点 (转换为小数)
                fee=fee                       # 使用找到的最佳费率
            )
            
            logger.info(f"交易已提交，交易哈希: {tx_hash.hex()}")
            logger.info(f"交易链接: {self.network_config['explorer']}{tx_hash.hex()}")
            
            # 等待交易确认
            logger.info("等待交易确认...")
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            
            if receipt['status'] == 1:
                # 获取交易后的代币余额
                _, new_balance, _ = self.get_token_balance(token_address)
                logger.info(f"交易成功! Gas使用: {receipt['gasUsed']}")
                logger.info(f"当前 {token_symbol} 余额: {new_balance}")
                return tx_hash.hex()
            else:
                logger.error(f"交易失败! Gas使用: {receipt['gasUsed']}")
                return None
                
        except Exception as e:
            logger.error(f"交易失败: {str(e)}")
            return None
    
    def token_to_eth(self, token_address, token_amount, slippage=1.0):
        """
        将代币交换为ETH
        
        Args:
            token_address: 代币合约地址
            token_amount: 要交换的代币数量
            slippage: 滑点百分比
            
        Returns:
            交易哈希或None（如果失败）
        """
        try:
            # 获取代币信息
            token_symbol, token_decimals = self.get_token_info(token_address)
            
            # 计算代币数量（以wei为单位）
            token_amount_wei = int(token_amount * (10 ** token_decimals))
            
            # 检查代币余额
            token_balance_wei, token_balance, _ = self.get_token_balance(token_address)
            if token_balance_wei < token_amount_wei:
                logger.error(f"代币余额不足: 需要 {token_amount} {token_symbol}，但只有 {token_balance} {token_symbol}")
                return None
            
            # 检查代币授权
            token_contract = self.web3.eth.contract(address=token_address, abi=ERC20_ABI)
            allowance = token_contract.functions.allowance(self.wallet_address, self.uniswap.address).call()
            if allowance < token_amount_wei:
                logger.info(f"需要授权 {token_symbol}")
                if not self.approve_token(token_address):
                    return None
            
            logger.info(f"卖出 {token_amount} {token_symbol} 换取ETH...")
            
            # 找到最佳费率
            fee, expected_eth = self.find_best_fee_rate(
                token_address,
                self.token_addresses["weth"],
                token_amount_wei
            )
            
            if fee is None:
                logger.error("无法找到可用的交易池")
                return None
            
            # 获取当前gas价格并适当提高
            gas_price = int(self.web3.eth.gas_price * 1.1)  # 增加10%
            logger.info(f"当前Gas价格: {self.web3.from_wei(gas_price, 'gwei')} Gwei")
            
            # 执行交换
            tx_hash = self.uniswap.make_trade(
                token_address,                # 输入代币
                self.token_addresses["weth"],  # 输出代币 (WETH)
                token_amount_wei,             # 输入金额
                slippage=slippage/100,        # 滑点 (转换为小数)
                fee=fee                       # 使用找到的最佳费率
            )
            
            logger.info(f"交易已提交，交易哈希: {tx_hash.hex()}")
            logger.info(f"交易链接: {self.network_config['explorer']}{tx_hash.hex()}")
            
            # 等待交易确认
            logger.info("等待交易确认...")
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            
            if receipt['status'] == 1:
                # 获取交易后的ETH余额
                eth_balance = self.web3.eth.get_balance(self.wallet_address)
                logger.info(f"交易成功! Gas使用: {receipt['gasUsed']}")
                logger.info(f"当前ETH余额: {self.web3.from_wei(eth_balance, 'ether')} ETH")
                return tx_hash.hex()
            else:
                logger.error(f"交易失败! Gas使用: {receipt['gasUsed']}")
                return None
                
        except Exception as e:
            logger.error(f"交易失败: {str(e)}")
            return None
    
    def get_token_address(self, token_symbol):
        """
        根据代币符号获取地址
        
        Args:
            token_symbol: 代币符号
            
        Returns:
            代币地址或None
        """
        token_symbol = token_symbol.lower()
        if token_symbol in self.token_addresses:
            return self.token_addresses[token_symbol]
        
        # 如果是ETH，返回WETH地址
        if token_symbol == "eth":
            return self.token_addresses["weth"]
        
        logger.error(f"未知的代币符号: {token_symbol}")
        return None

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Arbitrum网络上的Uniswap代币交换工具')
    parser.add_argument('--network', type=str, default='arbitrum', choices=['arbitrum', 'ethereum'],
                        help='要使用的网络 (默认: arbitrum)')
    parser.add_argument('--action', type=str, required=True, choices=['buy', 'sell'],
                        help='操作类型: buy (ETH到代币) 或 sell (代币到ETH)')
    parser.add_argument('--token', type=str, required=True,
                        help='代币符号 (例如: usdc, usdt, dai, wbtc) 或合约地址')
    parser.add_argument('--amount', type=float, required=True,
                        help='交易金额 (对于buy: ETH数量; 对于sell: 代币数量)')
    parser.add_argument('--slippage', type=float, default=1.0,
                        help='滑点百分比 (默认: 1.0)')
    
    args = parser.parse_args()
    
    try:
        # 初始化交换器
        swapper = ArbitrumSwapper(network=args.network)
        
        # 获取代币地址
        token = args.token
        if not token.startswith('0x'):
            token_address = swapper.get_token_address(token)
            if not token_address:
                logger.error(f"未知的代币: {token}")
                return
        else:
            token_address = Web3.to_checksum_address(token)
        
        # 执行操作
        if args.action == 'buy':
            # ETH到代币
            result = swapper.eth_to_token(token_address, args.amount, slippage=args.slippage)
            if result:
                token_symbol, _ = swapper.get_token_info(token_address)
                print(f"✅ 成功购买代币! 使用 {args.amount} ETH 购买了 {token_symbol}")
                print(f"交易哈希: {result}")
                print(f"交易链接: {swapper.network_config['explorer']}{result}")
            else:
                print(f"❌ 购买失败!")
                
        elif args.action == 'sell':
            # 代币到ETH
            result = swapper.token_to_eth(token_address, args.amount, slippage=args.slippage)
            if result:
                token_symbol, _ = swapper.get_token_info(token_address)
                print(f"✅ 成功卖出代币! 卖出 {args.amount} {token_symbol} 获得了 ETH")
                print(f"交易哈希: {result}")
                print(f"交易链接: {swapper.network_config['explorer']}{result}")
            else:
                print(f"❌ 卖出失败!")
    
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        print(f"❌ 操作失败: {str(e)}")

if __name__ == "__main__":
    main()

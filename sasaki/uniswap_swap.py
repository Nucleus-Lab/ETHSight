import os
from web3 import Web3
from uniswap import Uniswap
from dotenv import load_dotenv
import logging
import time
from enum import Enum

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 定义网络类型
class Network(Enum):
    MAINNET = "mainnet"
    ARBITRUM = "arbitrum"

# 网络配置
NETWORK_CONFIG = {
    Network.MAINNET: {
        "rpc": "https://mainnet.infura.io/v3/{}",
        "chain_id": 1
    },
    Network.ARBITRUM: {
        "rpc": "https://arbitrum-mainnet.infura.io/v3/{}",
        "chain_id": 42161
    }
}

# 常用代币地址 (按网络)
TOKEN_ADDRESSES = {
    Network.MAINNET: {
        "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599"
    },
    Network.ARBITRUM: {
        "WETH": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
        "USDC": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
        "DAI": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
        "USDT": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
        "WBTC": "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f"
    }
}

class UniswapTrader:
    def __init__(self, network=Network.ARBITRUM):
        """初始化Uniswap交易类"""
        # 设置网络
        self.network = network
        self.token_addresses = TOKEN_ADDRESSES[self.network]
        self.network_config = NETWORK_CONFIG[self.network]
        
        # 从环境变量获取配置
        self.infura_key = os.getenv("INFURA_KEY")
        self.wallet_address = os.getenv("WALLET_ADDRESS")
        self.private_key = os.getenv("PRIVATE_KEY")
        
        if not all([self.infura_key, self.wallet_address, self.private_key]):
            logger.error("环境变量未设置完全。请确保设置了INFURA_KEY, WALLET_ADDRESS和PRIVATE_KEY")
            raise ValueError("缺少必要的环境变量")
        
        # 设置RPC URL
        self.provider_url = self.network_config["rpc"].format(self.infura_key)
        
        # 初始化Web3连接
        self.web3 = Web3(Web3.HTTPProvider(self.provider_url))
        
        # 检查连接
        if not self.web3.is_connected():
            logger.error(f"无法连接到以太坊网络: {self.provider_url}")
            raise ConnectionError("Web3连接失败")
        
        logger.info(f"成功连接到以太坊网络，当前区块: {self.web3.eth.block_number}")
        
        # 初始化Uniswap客户端 (默认使用v2版本)
        self.uniswap_v2 = Uniswap(
            address=self.wallet_address,
            private_key=self.private_key,
            version=2,
            provider=self.provider_url,
            # 不使用network参数，而是通过正确的RPC端点来支持不同网络
        )
        
        # 初始化Uniswap v3客户端
        self.uniswap_v3 = Uniswap(
            address=self.wallet_address,
            private_key=self.private_key,
            version=3,
            provider=self.provider_url,
            # 不使用network参数，而是通过正确的RPC端点来支持不同网络
        )
        
        logger.info("Uniswap交易类初始化完成")
    
    def get_token_balance(self, token_address):
        """获取指定代币的余额
        
        Args:
            token_address (str): 代币合约地址
            
        Returns:
            float: 代币余额
        """
        try:
            # 对于ETH，直接获取账户余额
            if token_address.lower() == "eth":
                balance_wei = self.web3.eth.get_balance(self.wallet_address)
                balance = self.web3.from_wei(balance_wei, 'ether')
                logger.info(f"ETH余额: {balance}")
                return float(balance)
            
            # 对于ERC20代币，使用Uniswap库获取余额
            balance = self.uniswap_v2.get_token_balance(token_address)
            decimals = self.uniswap_v2.get_token_decimals(token_address)
            adjusted_balance = balance / (10 ** decimals)
            
            token_symbol = self.uniswap_v2.get_token_symbol(token_address)
            logger.info(f"{token_symbol}余额: {adjusted_balance}")
            
            return adjusted_balance
        except Exception as e:
            logger.error(f"获取代币余额失败: {str(e)}")
            return 0
    
    def get_token_price(self, token_address, price_in="eth"):
        """获取代币价格
        
        Args:
            token_address (str): 代币合约地址
            price_in (str): 价格单位，可选 'eth' 或 'usd'
            
        Returns:
            float: 代币价格
        """
        try:
            if price_in.lower() == "eth":
                # 获取以ETH为单位的价格
                price = self.uniswap_v2.get_price_input(WETH, token_address, 10**18)
                price_eth = 1 / (price / 10**18)
                logger.info(f"代币价格: {price_eth} ETH")
                return price_eth
            else:
                # 获取以USDC为单位的价格
                price = self.uniswap_v2.get_price_input(USDC, token_address, 10**6)
                price_usd = 1 / (price / 10**6)
                logger.info(f"代币价格: {price_usd} USD")
                return price_usd
        except Exception as e:
            logger.error(f"获取代币价格失败: {str(e)}")
            return 0
    
    def swap_eth_for_token(self, token_address, eth_amount, slippage=0.5, version=2):
        """使用ETH购买代币
        
        Args:
            token_address (str): 目标代币地址
            eth_amount (float): 要使用的ETH数量
            slippage (float): 滑点百分比
            version (int): Uniswap版本 (2或3)
            
        Returns:
            str: 交易哈希
        """
        """使用ETH购买代币
        
        Args:
            token_address (str): 目标代币地址
            eth_amount (float): 要使用的ETH数量
            slippage (float): 滑点百分比
            version (int): Uniswap版本 (2或3)
            
        Returns:
            str: 交易哈希
        """
        try:
            # 选择Uniswap版本
            uniswap = self.uniswap_v2 if version == 2 else self.uniswap_v3
            
            # 将ETH数量转换为Wei
            eth_amount_wei = self.web3.to_wei(eth_amount, 'ether')
            
            # 获取代币符号
            token_symbol = uniswap.get_token_symbol(token_address)
            
            logger.info(f"开始交易: {eth_amount} ETH -> {token_symbol}")
            logger.info(f"使用Uniswap v{version}, 滑点: {slippage}%")
            
            # 执行交易
            tx_hash = uniswap.make_trade_output(
                self.token_addresses["WETH"],  # 输入代币 (WETH)
                token_address,               # 输出代币
                eth_amount_wei,              # 输入金额
                slippage=slippage/100        # 滑点 (转换为小数)
            )
            
            logger.info(f"交易已提交，交易哈希: {tx_hash.hex()}")
            
            # 等待交易确认
            logger.info("等待交易确认...")
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                logger.info(f"交易成功! Gas使用: {receipt['gasUsed']}")
            else:
                logger.error(f"交易失败! Gas使用: {receipt['gasUsed']}")
            
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"交易失败: {str(e)}")
            return None
    
    def swap_token_for_eth(self, token_address, token_amount, slippage=0.5, version=2):
        """将代币卖出换成ETH
        
        Args:
            token_address (str): 要卖出的代币地址
            token_amount (float): 要卖出的代币数量
            slippage (float): 滑点百分比
            version (int): Uniswap版本 (2或3)
            
        Returns:
            str: 交易哈希
        """
        try:
            # 选择Uniswap版本
            uniswap = self.uniswap_v2 if version == 2 else self.uniswap_v3
            
            # 获取代币信息
            token_symbol = uniswap.get_token_symbol(token_address)
            token_decimals = uniswap.get_token_decimals(token_address)
            
            # 将代币数量转换为最小单位
            token_amount_wei = int(token_amount * (10 ** token_decimals))
            
            logger.info(f"开始交易: {token_amount} {token_symbol} -> ETH")
            logger.info(f"使用Uniswap v{version}, 滑点: {slippage}%")
            
            # 检查授权
            allowance = uniswap.get_token_allowance(token_address)
            if allowance < token_amount_wei:
                logger.info(f"需要授权代币使用权...")
                uniswap.approve_token(token_address)
                time.sleep(30)  # 等待授权确认
            
            # 执行交易
            tx_hash = uniswap.make_trade(
                token_address,               # 输入代币
                self.token_addresses["WETH"],  # 输出代币 (WETH)
                token_amount_wei,            # 输入金额
                slippage=slippage/100        # 滑点 (转换为小数)
            )
            
            logger.info(f"交易已提交，交易哈希: {tx_hash.hex()}")
            
            # 等待交易确认
            logger.info("等待交易确认...")
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                logger.info(f"交易成功! Gas使用: {receipt['gasUsed']}")
            else:
                logger.error(f"交易失败! Gas使用: {receipt['gasUsed']}")
            
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"交易失败: {str(e)}")
            return None


# 示例用法
if __name__ == "__main__":
    try:
        # 创建交易实例 (可以选择网络)
        # trader = UniswapTrader(network=Network.MAINNET)  # 以太坊主网
        trader = UniswapTrader()  # 默认使用Arbitrum
        
        # 获取ETH余额
        eth_balance = trader.get_token_balance("eth")
        print(f"当前ETH余额: {eth_balance}")
        
        # 获取USDC余额
        usdc_balance = trader.get_token_balance(trader.token_addresses["USDC"])
        print(f"当前USDC余额: {usdc_balance}")
        
        # 获取代币价格
        # usdc_price = trader.get_token_price(trader.token_addresses["USDC"], price_in="eth")
        # print(f"USDC价格: {usdc_price} ETH")
        
        # 示例交易 (注释掉以防止意外执行)
        # 使用0.01 ETH购买USDC
        # tx_hash = trader.swap_eth_for_token(trader.token_addresses["USDC"], 0.01)
        # print(f"交易哈希: {tx_hash}")
        
        # 卖出10 USDC换回ETH
        # tx_hash = trader.swap_token_for_eth(trader.token_addresses["USDC"], 10)
        # print(f"交易哈希: {tx_hash}")
        
    except Exception as e:
        print(f"发生错误: {str(e)}")

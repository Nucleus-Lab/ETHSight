import os
import json
import logging
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv
from web3.middleware import SignAndSendRawMiddlewareBuilder
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Uniswap V2 Router address on Sepolia
UNISWAP_ROUTER_ADDRESS = "0xeE567Fe1712Faf6149d80dA1E6934E354124CfE3"  # Sepolia Router
WETH_ADDRESS = "0x7b79995e5f793A07Bc00c21412e50Ecae098E7f9"  # WETH on Sepolia

# Load Router ABI
with open('abis/UniswapV2Router02.json', 'r') as f:
    ROUTER_ABI = json.load(f)

class UniswapTrader:
    def __init__(self, private_key: str, rpc_url: str):
        """
        Initialize Uniswap trader with private key and RPC URL
        """
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise Exception("Failed to connect to the network")
            
        self.account = Account.from_key(private_key)
        
        # Add middleware for auto-signing transactions
        self.w3.middleware_onion.inject(SignAndSendRawMiddlewareBuilder.build(self.account), layer=0)
        
        self.router = self.w3.eth.contract(
            address=Web3.to_checksum_address(UNISWAP_ROUTER_ADDRESS),
            abi=ROUTER_ABI
        )
        logger.info(f"Connected to network: {self.w3.eth.chain_id}")
        logger.info(f"Account address: {self.account.address}")
        
        # Verify router contract
        try:
            factory_address = self.router.functions.factory().call()
            logger.info(f"Uniswap Factory address: {factory_address}")
            
            # Load Factory ABI (minimal version for pair checks)
            factory_abi = [{"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"}],"name":"getPair","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"}]
            self.factory = self.w3.eth.contract(address=factory_address, abi=factory_abi)
            
        except Exception as e:
            logger.error(f"Failed to connect to Uniswap Router: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def check_pair_exists(self, token0: str, token1: str) -> bool:
        """
        Check if a trading pair exists
        """
        try:
            pair_address = self.factory.functions.getPair(
                Web3.to_checksum_address(token0),
                Web3.to_checksum_address(token1)
            ).call()
            
            if pair_address == "0x0000000000000000000000000000000000000000":
                logger.error(f"No liquidity pool exists for {token0} and {token1}")
                return False
                
            logger.info(f"Found liquidity pool at: {pair_address}")
            return True
            
        except Exception as e:
            logger.error(f"Error checking pair: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def get_token_balance(self, token_address: str) -> float:
        """
        Get token balance for the connected wallet
        """
        try:
            token_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=[{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]
            )
            balance = token_contract.functions.balanceOf(self.account.address).call()
            return self.w3.from_wei(balance, 'ether')
        except Exception as e:
            logger.error(f"Error getting token balance: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def swap_exact_eth_for_tokens(self, token_address: str, amount_eth: float, slippage: float = 0.5):
        """
        Swap exact ETH for tokens
        """
        try:
            # Check if pair exists
            if not self.check_pair_exists(WETH_ADDRESS, token_address):
                raise Exception("No liquidity pool exists for this pair")
                
            amount_eth_wei = self.w3.to_wei(amount_eth, 'ether')
            deadline = self.w3.eth.get_block('latest').timestamp + 300  # 5 minutes
            
            # Get minimum amount out with slippage
            amounts_out = self.router.functions.getAmountsOut(
                amount_eth_wei,
                [WETH_ADDRESS, token_address]
            ).call()
            
            min_amount_out = int(amounts_out[1] * (1 - slippage / 100))
            
            logger.info(f"Expected output amount: {self.w3.from_wei(amounts_out[1], 'ether')} tokens")
            logger.info(f"Minimum output amount with {slippage}% slippage: {self.w3.from_wei(min_amount_out, 'ether')} tokens")
            
            # Build transaction
            tx = self.router.functions.swapExactETHForTokens(
                min_amount_out,
                [WETH_ADDRESS, token_address],
                self.account.address,
                deadline
            ).build_transaction({
                'from': self.account.address,
                'value': amount_eth_wei,
                'gas': 250000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
            })
            
            # Send transaction using middleware
            tx_hash = self.w3.eth.send_transaction(tx)
            logger.info(f"Transaction sent: {tx_hash.hex()}")
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            logger.info(f"Transaction status: {'success' if receipt['status'] == 1 else 'failed'}")
            
            return receipt
            
        except Exception as e:
            logger.error(f"Error in swap_exact_eth_for_tokens: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def swap_exact_tokens_for_eth(self, token_address: str, amount_tokens: float, slippage: float = 0.5):
        """
        Swap exact tokens for ETH
        """
        try:
            # Check if pair exists
            if not self.check_pair_exists(token_address, WETH_ADDRESS):
                raise Exception("No liquidity pool exists for this pair")
                
            token_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=[{"constant":False,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"}]
            )
            
            amount_tokens_wei = self.w3.to_wei(amount_tokens, 'ether')
            deadline = self.w3.eth.get_block('latest').timestamp + 300  # 5 minutes
            
            # Check current allowance
            allowance = token_contract.functions.allowance(
                self.account.address,
                UNISWAP_ROUTER_ADDRESS
            ).call()
            
            if allowance < amount_tokens_wei:
                logger.info("Approving token spend...")
                # Approve router to spend tokens
                approve_tx = token_contract.functions.approve(
                    UNISWAP_ROUTER_ADDRESS,
                    amount_tokens_wei
                ).build_transaction({
                    'from': self.account.address,
                    'gas': 100000,
                    'gasPrice': self.w3.eth.gas_price,
                    'nonce': self.w3.eth.get_transaction_count(self.account.address),
                })
                
                # Send approval transaction using middleware
                approve_tx_hash = self.w3.eth.send_transaction(approve_tx)
                self.w3.eth.wait_for_transaction_receipt(approve_tx_hash)
                logger.info("Token approval successful")
            
            # Get minimum amount out with slippage
            amounts_out = self.router.functions.getAmountsOut(
                amount_tokens_wei,
                [token_address, WETH_ADDRESS]
            ).call()
            
            min_amount_out = int(amounts_out[1] * (1 - slippage / 100))
            
            logger.info(f"Expected output amount: {self.w3.from_wei(amounts_out[1], 'ether')} ETH")
            logger.info(f"Minimum output amount with {slippage}% slippage: {self.w3.from_wei(min_amount_out, 'ether')} ETH")
            
            # Build swap transaction
            swap_tx = self.router.functions.swapExactTokensForETH(
                amount_tokens_wei,
                min_amount_out,
                [token_address, WETH_ADDRESS],
                self.account.address,
                deadline
            ).build_transaction({
                'from': self.account.address,
                'gas': 250000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
            })
            
            # Send swap transaction using middleware
            swap_tx_hash = self.w3.eth.send_transaction(swap_tx)
            logger.info(f"Transaction sent: {swap_tx_hash.hex()}")
            
            receipt = self.w3.eth.wait_for_transaction_receipt(swap_tx_hash)
            logger.info(f"Transaction status: {'success' if receipt['status'] == 1 else 'failed'}")
            
            return receipt
            
        except Exception as e:
            logger.error(f"Error in swap_exact_tokens_for_eth: {str(e)}")
            logger.error(traceback.format_exc())
            raise

def main():
    # Load environment variables
    private_key = os.getenv('PRIVATE_KEY')
    rpc_url = os.getenv('SEPOLIA_RPC_URL')
    
    if not private_key or not rpc_url:
        logger.error("Please set PRIVATE_KEY and SEPOLIA_RPC_URL in .env file")
        return
    
    # Initialize trader
    trader = UniswapTrader(private_key, rpc_url)
    
    # USDC token address on Sepolia
    token_address = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"
    
    try:
        # Get initial balances
        eth_balance = trader.w3.eth.get_balance(trader.account.address)
        token_balance = trader.get_token_balance(token_address)
        logger.info(f"Initial ETH balance: {trader.w3.from_wei(eth_balance, 'ether')}")
        logger.info(f"Initial token balance: {token_balance}")
        
        # Example: Swap 0.001 ETH for tokens
        logger.info("Swapping ETH for tokens...")
        trader.swap_exact_eth_for_tokens(token_address, 0.001)
        
        # Get intermediate balances
        eth_balance = trader.w3.eth.get_balance(trader.account.address)
        token_balance = trader.get_token_balance(token_address)
        logger.info(f"Intermediate ETH balance: {trader.w3.from_wei(eth_balance, 'ether')}")
        logger.info(f"Intermediate token balance: {token_balance}")
        
        # Example: Swap tokens back to ETH
        logger.info("Swapping tokens back to ETH...")
        trader.swap_exact_tokens_for_eth(token_address, 1)  # Amount in tokens
        
        # Get final balances
        eth_balance = trader.w3.eth.get_balance(trader.account.address)
        token_balance = trader.get_token_balance(token_address)
        logger.info(f"Final ETH balance: {trader.w3.from_wei(eth_balance, 'ether')}")
        logger.info(f"Final token balance: {token_balance}")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()

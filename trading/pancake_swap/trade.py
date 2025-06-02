from web3 import Web3
import os
import json
import time
from dotenv import load_dotenv

load_dotenv()

# Load environment variables
PRIVATE_KEY = os.getenv('PRIVATE_KEY')
WALLET_ADDRESS = os.getenv('WALLET_ADDRESS')
BSC_TESTNET_RPC_URL = os.getenv('BSC_TESTNET_RPC_URL')

bsc_testnet = Web3(Web3.HTTPProvider(BSC_TESTNET_RPC_URL))
assert bsc_testnet.is_connected(), "Failed to connect to BSC Testnet"

# pancake swap router address on BSC Testnet
router_address = Web3.to_checksum_address("0x9a489505a00cE272eAa5e07Dba6491314CaE3796")
with open('abis/PancakeSwapSmartRouter.json') as f:
    router_abi = json.load(f)
router = bsc_testnet.eth.contract(address=router_address, abi=router_abi)
print("router", router)

# get the amount of BNB in the wallet
bnb_balance = bsc_testnet.eth.get_balance(WALLET_ADDRESS)
print(f"BNB balance: {bnb_balance / 10**18} BNB")

# Token addresses for BSC Testnet
WBNB = Web3.to_checksum_address('0xae13d989daC2f0dEbFf460aC112a837C89BAa7cd')  # Testnet WBNB
CAKE = Web3.to_checksum_address('0xFa60D973F7642B748046464e165A65B7323b0DEE')  # Testnet CAKE

# Swap parameters
amount_in = bsc_testnet.to_wei(0.01, 'ether')  # Amount of BNB to swap
amount_out_min = 0  # Set according to slippage tolerance
deadline = int(time.time()) + 60 * 10  # 10 minutes from now

# For swapping exact BNB to tokens, we'll use exactInputSingle
params = {
    'tokenIn': WBNB,
    'tokenOut': CAKE,
    'fee': 2500,  # 0.25% fee tier
    'recipient': WALLET_ADDRESS,
    'amountIn': amount_in,
    'amountOutMinimum': amount_out_min,
    'sqrtPriceLimitX96': 0  # No price limit
}

# Build transaction
txn = router.functions.exactInputSingle(params).build_transaction({
    'from': WALLET_ADDRESS,
    'value': amount_in,  # Send BNB with the transaction
    'gas': 300000,  # Increased gas limit for safety
    'gasPrice': bsc_testnet.to_wei('5', 'gwei'),
    'nonce': bsc_testnet.eth.get_transaction_count(WALLET_ADDRESS),
    'chainId': 97  # BSC Testnet chain ID
})

# Estimate gas
gas = bsc_testnet.eth.estimate_gas({'from': WALLET_ADDRESS, 'to': router_address, 'data': txn['data'], 'value': amount_in})
txn['gas'] = gas

print("gas", gas)

# Sign and send transaction
signed_txn = bsc_testnet.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
tx_hash = bsc_testnet.eth.send_raw_transaction(signed_txn.raw_transaction)

print(f'Transaction sent: {tx_hash.hex()}')


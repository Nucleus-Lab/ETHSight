from web3 import Web3
import os

# 初始化
infura_url = "https://mainnet.infura.io/v3/YOUR_INFURA_KEY"
web3 = Web3(Web3.HTTPProvider(infura_url))

my_address = "YOUR_WALLET"
private_key = "YOUR_PRIVATE_KEY"

# Uniswap V2 Router 合约
router_address = Web3.to_checksum_address("0x7a250d5630B4cF539739df2C5dAcb4c659F2488D")
router_abi = [...]  # 从Etherscan导入UniswapV2Router ABI

router = web3.eth.contract(address=router_address, abi=router_abi)

def buy_token():
    amount_in_wei = Web3.to_wei(0.01, 'ether')
    token_address = "0x..."  # CA
    path = [Web3.to_checksum_address(web3.to_checksum_address("0xC02aaa...")),  # WETH
            Web3.to_checksum_address(token_address)]

    deadline = int(web3.eth.get_block('latest').timestamp) + 60 * 10
    txn = router.functions.swapExactETHForTokens(
        0,
        path,
        my_address,
        deadline
    ).build_transaction({
        'from': my_address,
        'value': amount_in_wei,
        'gas': 250000,
        'gasPrice': web3.to_wei('30', 'gwei'),
        'nonce': web3.eth.get_transaction_count(my_address)
    })

    signed_txn = web3.eth.account.sign_transaction(txn, private_key=private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    print("🚀 Transaction sent:", web3.to_hex(tx_hash))
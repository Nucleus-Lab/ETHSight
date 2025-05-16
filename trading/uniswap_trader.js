const { ethers } = require('ethers');
require('dotenv').config();

// Configure logging
const logger = {
    info: (message) => console.log(`[INFO] ${new Date().toISOString()} - ${message}`),
    error: (message) => console.error(`[ERROR] ${new Date().toISOString()} - ${message}`)
};

// Uniswap V2 Router address on Arbitrum
const UNISWAP_ROUTER_ADDRESS = "0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24";
const WETH_ADDRESS = "0x82af49447d8a07e3bd95bd0d56f35241523fbab1";

// Minimal Router ABI for our needs
const ROUTER_ABI = [
    "function factory() external view returns (address)",
    "function getAmountsOut(uint amountIn, address[] memory path) public view returns (uint[] memory amounts)",
    "function swapExactETHForTokens(uint amountOutMin, address[] calldata path, address to, uint deadline) external payable returns (uint[] memory amounts)",
    "function swapExactTokensForETH(uint amountIn, uint amountOutMin, address[] calldata path, address to, uint deadline) external returns (uint[] memory amounts)"
];

// Minimal Factory ABI for pair checks
const FACTORY_ABI = [
    "function getPair(address tokenA, address tokenB) external view returns (address pair)"
];

// Minimal ERC20 ABI for token operations
const ERC20_ABI = [
    "function balanceOf(address owner) view returns (uint256)",
    "function approve(address spender, uint256 amount) external returns (bool)",
    "function allowance(address owner, address spender) view returns (uint256)"
];

class UniswapTrader {
    constructor(privateKey, rpcUrl) {
        try {
            // Initialize provider and wallet
            this.provider = new ethers.JsonRpcProvider(rpcUrl);
            this.wallet = new ethers.Wallet(privateKey, this.provider);
            
            // Initialize contracts
            this.router = new ethers.Contract(UNISWAP_ROUTER_ADDRESS, ROUTER_ABI, this.wallet);
            
            // Token decimals mapping
            this.tokenDecimals = {
                "0xaf88d065e77c8cC2239327C5EDb3A432268e5831": 6  // USDC on Arbitrum
            };
            
            logger.info(`Account address: ${this.wallet.address}`);
        } catch (error) {
            logger.error(`Failed to initialize trader: ${error.message}`);
            throw error;
        }
    }

    async initialize() {
        try {
            // Wait for provider to be ready and get network information
            const network = await this.provider.getNetwork();
            logger.info(`Connected to network: ${network.chainId}`);
            
            // Initialize factory contract
            await this.initializeFactory();
            return true;
        } catch (error) {
            logger.error(`Failed to initialize network connection: ${error.message}`);
            throw error;
        }
    }

    async initializeFactory() {
        try {
            const factoryAddress = await this.router.factory();
            this.factory = new ethers.Contract(factoryAddress, FACTORY_ABI, this.wallet);
            logger.info(`Uniswap Factory address: ${factoryAddress}`);
        } catch (error) {
            logger.error(`Failed to connect to Uniswap Router: ${error.message}`);
            throw error;
        }
    }

    async checkPairExists(token0, token1) {
        try {
            const pairAddress = await this.factory.getPair(token0, token1);
            
            if (pairAddress === ethers.ZeroAddress) {
                logger.error(`No liquidity pool exists for ${token0} and ${token1}`);
                return false;
            }
            
            logger.info(`Found liquidity pool at: ${pairAddress}`);
            return true;
        } catch (error) {
            logger.error(`Error checking pair: ${error.message}`);
            return false;
        }
    }

    async getTokenDecimals(tokenAddress) {
        if (this.tokenDecimals[tokenAddress]) {
            return this.tokenDecimals[tokenAddress];
        }
        
        try {
            const tokenContract = new ethers.Contract(tokenAddress, [
                "function decimals() view returns (uint8)"
            ], this.provider);
            const decimals = await tokenContract.decimals();
            this.tokenDecimals[tokenAddress] = decimals;
            return decimals;
        } catch (error) {
            logger.error(`Error getting token decimals: ${error.message}`);
            return 18; // Default to 18 if unable to get decimals
        }
    }

    async getTokenBalance(tokenAddress) {
        try {
            const tokenContract = new ethers.Contract(tokenAddress, ERC20_ABI, this.wallet);
            const decimals = await this.getTokenDecimals(tokenAddress);
            const balance = await tokenContract.balanceOf(this.wallet.address);
            return ethers.formatUnits(balance, decimals);
        } catch (error) {
            logger.error(`Error getting token balance: ${error.message}`);
            throw error;
        }
    }

    async swapExactEthForTokens(tokenAddress, amountEth, slippage = 0.5) {
        try {
            // Check if pair exists
            if (!await this.checkPairExists(WETH_ADDRESS, tokenAddress)) {
                throw new Error("No liquidity pool exists for this pair");
            }

            const amountEthWei = ethers.parseEther(amountEth.toString());
            const deadline = Math.floor(Date.now() / 1000) + 300; // 5 minutes

            // Get minimum amount out with slippage
            const amountsOut = await this.router.getAmountsOut(
                amountEthWei,
                [WETH_ADDRESS, tokenAddress]
            );

            logger.info(`Swap path: [${WETH_ADDRESS}, ${tokenAddress}]`);

            const minAmountOut = amountsOut[1] * BigInt(Math.floor((1 - slippage / 100) * 1000)) / BigInt(1000);

            logger.info(`Expected output amount: ${ethers.formatEther(amountsOut[1])} tokens`);
            logger.info(`Minimum output amount with ${slippage}% slippage: ${ethers.formatEther(minAmountOut)} tokens`);

            // Build and send transaction
            const tx = await this.router.swapExactETHForTokens(
                minAmountOut,
                [WETH_ADDRESS, tokenAddress],
                this.wallet.address,
                deadline,
                { value: amountEthWei }
            );

            logger.info(`Transaction sent: ${tx.hash}`);
            const receipt = await tx.wait();
            logger.info(`Transaction status: ${receipt.status === 1 ? 'success' : 'failed'}`);

            return receipt;
        } catch (error) {
            logger.error(`Error in swapExactEthForTokens: ${error.message}`);
            throw error;
        }
    }

    async swapExactTokensForEth(tokenAddress, amountTokens, slippage = 0.5) {
        try {
            // Check if pair exists
            if (!await this.checkPairExists(tokenAddress, WETH_ADDRESS)) {
                throw new Error("No liquidity pool exists for this pair");
            }

            const tokenContract = new ethers.Contract(tokenAddress, ERC20_ABI, this.wallet);
            const decimals = await this.getTokenDecimals(tokenAddress);
            const amountTokensWei = ethers.parseUnits(amountTokens.toString(), decimals);
            
            logger.info(`Attempting to swap ${amountTokens} tokens (${amountTokensWei} base units) back to ETH`);
            
            const deadline = Math.floor(Date.now() / 1000) + 300; // 5 minutes

            // Check current allowance
            const allowance = await tokenContract.allowance(
                this.wallet.address,
                UNISWAP_ROUTER_ADDRESS
            );

            if (allowance < amountTokensWei) {
                logger.info(`Approving token spend for ${tokenAddress} with the amount of ${amountTokensWei} (${amountTokens} tokens)...`);
                const approveTx = await tokenContract.approve(
                    UNISWAP_ROUTER_ADDRESS,
                    amountTokensWei
                );
                await approveTx.wait();
                logger.info("Token approval successful");
            }

            // Get minimum amount out with slippage
            const amountsOut = await this.router.getAmountsOut(
                amountTokensWei,
                [tokenAddress, WETH_ADDRESS]
            );

            const minAmountOut = amountsOut[1] * BigInt(Math.floor((1 - slippage / 100) * 1000)) / BigInt(1000);

            logger.info(`Expected output amount: ${ethers.formatEther(amountsOut[1])} ETH`);
            logger.info(`Minimum output amount with ${slippage}% slippage: ${ethers.formatEther(minAmountOut)} ETH`);

            // Build and send transaction
            const tx = await this.router.swapExactTokensForETH(
                amountTokensWei,
                minAmountOut,
                [tokenAddress, WETH_ADDRESS],
                this.wallet.address,
                deadline
            );

            logger.info(`Transaction sent: ${tx.hash}`);
            const receipt = await tx.wait();
            logger.info(`Transaction status: ${receipt.status === 1 ? 'success' : 'failed'}`);

            return receipt;
        } catch (error) {
            logger.error(`Error in swapExactTokensForEth: ${error.message}`);
            throw error;
        }
    }
}

async function main() {
    // Load environment variables
    const privateKey = process.env.PRIVATE_KEY;
    const rpcUrl = process.env.ARBITRUM_RPC_URL;

    if (!privateKey || !rpcUrl) {
        logger.error("Please set PRIVATE_KEY and ARBITRUM_RPC_URL in .env file");
        return;
    }

    try {
        // Initialize trader
        const trader = new UniswapTrader(privateKey, rpcUrl);
        
        // Initialize the trader with network connection
        await trader.initialize();

        // USDC token address on Arbitrum
        const tokenAddress = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831";

        // Get initial balances
        const ethBalance = await trader.provider.getBalance(trader.wallet.address);
        const tokenBalance = await trader.getTokenBalance(tokenAddress);
        logger.info(`Initial ETH balance: ${ethers.formatEther(ethBalance)}`);
        logger.info(`Initial token balance: ${tokenBalance}`);

        // Example: Swap 0.001 ETH for tokens
        logger.info("Swapping ETH for tokens...");
        await trader.swapExactEthForTokens(tokenAddress, 0.001);

        // Get intermediate balances
        const ethBalance2 = await trader.provider.getBalance(trader.wallet.address);
        const tokenBalance2 = await trader.getTokenBalance(tokenAddress);
        logger.info(`Intermediate ETH balance: ${ethers.formatEther(ethBalance2)}`);
        logger.info(`Intermediate token balance: ${tokenBalance2}`);

        // Example: Swap tokens back to ETH - use the actual token balance we received
        logger.info("Swapping tokens back to ETH...");
        await trader.swapExactTokensForEth(tokenAddress, tokenBalance2); // Use actual token balance

        // Get final balances
        const ethBalance3 = await trader.provider.getBalance(trader.wallet.address);
        const tokenBalance3 = await trader.getTokenBalance(tokenAddress);
        logger.info(`Final ETH balance: ${ethers.formatEther(ethBalance3)}`);
        logger.info(`Final token balance: ${tokenBalance3}`);

    } catch (error) {
        logger.error(`Error in main: ${error.message}`);
    }
}

// Run the main function
main().catch(console.error); 
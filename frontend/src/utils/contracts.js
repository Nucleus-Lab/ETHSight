import { ethers } from 'ethers';
import SubscriptionNFT from '../assets/abi/SubscriptionNFT.json';

// Contract address - replace with your deployed contract address
// const CONTRACT_ADDRESS = "0xD63878fcE308FDc2864B296334d96403910EDb77";  // Garfield testnet
const CONTRACT_ADDRESS = "0xCe4a81bc23e5DA5466b3421EBb9b961b07aBd9A9";  // Base Sepolia testnet
// const CHAIN_ID = "0xBF02";    // chain id for Garfield testnet
const CHAIN_ID = "0x14A34";    // chain id for Base Sepolia testnet

// Helper function to get signer from Privy wallet
export const getSigner = async (wallet) => {
  try {
    console.log("Getting signer from wallet:", wallet.address);
    
    // Get the provider and switch chain using JSON-RPC
    const provider = await wallet.getEthereumProvider();
    try {
      console.log("Switching to target network");
      await provider.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: CHAIN_ID }],
      });
    } catch (switchError) {
      throw switchError;
    }

    const ethersProvider = new ethers.BrowserProvider(provider);
    const signer = await ethersProvider.getSigner();
    console.log("Successfully got signer");
    return signer;
  } catch (error) {
    console.error("Error getting signer:", error);
    throw error;
  }
};

// Helper function to check if contract exists
const checkContractExists = async (provider, address) => {
  try {
    const code = await provider.getCode(address);
    console.log("Contract code at address:", code);
    return code !== "0x";
  } catch (error) {
    console.error("Error checking contract existence:", error);
    return false;
  }
};

export const getContract = async (wallet) => {
  try {
    const signer = await getSigner(wallet);
    const provider = signer.provider;
    
    // Check if contract exists
    const exists = await checkContractExists(provider, CONTRACT_ADDRESS);
    if (!exists) {
      throw new Error(`No contract found at address ${CONTRACT_ADDRESS}. Please make sure the contract is deployed.`);
    }

    const contract = new ethers.Contract(
      CONTRACT_ADDRESS,
      SubscriptionNFT.abi,
      signer
    );
    console.log("Contract instance created successfully");
    return contract;
  } catch (error) {
    console.error("Error creating contract instance:", error);
    throw error;
  }
};

export const checkSubscription = async (address, wallet) => {
  try {
    console.log("Checking subscription for address:", address);
    const contract = await getContract(wallet);
    
    // First check if the contract exists and is accessible
    try {
      await contract.name(); // Try to call a simple view function
    } catch (error) {
      console.error("Error accessing contract:", error);
      throw new Error("Contract is not accessible. Please check if it's properly deployed.");
    }

    console.log("Calling getUserSubscription...");
    const tokenId = await contract.getUserSubscription(address);
    console.log("Raw tokenId:", tokenId);

    // Handle different possible return values
    if (!tokenId || tokenId === "0x" || tokenId === "0" || tokenId.toString() === "0") {
      console.log("No active subscription found");
      return {
        hasSubscription: false,
        expiryDate: null
      };
    }

    console.log("Token ID:", tokenId.toString());
    
    const expiryTimestamp = await contract.getSubscriptionExpiry(tokenId);
    console.log("Raw expiryTimestamp:", expiryTimestamp, "Type:", typeof expiryTimestamp);
    
    // Convert BigInt to number before multiplying
    const expiryTimestampNumber = Number(expiryTimestamp);
    const expiryDate = new Date(expiryTimestampNumber * 1000);
    
    console.log("Subscription expiry date:", expiryDate);
    
    return {
      hasSubscription: true,
      expiryDate: expiryDate
    };
  } catch (error) {
    console.error("Error checking subscription:", error);
    throw error;
  }
};

export const subscribe = async (wallet) => {
  try {
    console.log("Initiating subscription process");
    const contract = await getContract(wallet);
    
    // Verify contract is accessible
    try {
      await contract.name();
    } catch (error) {
      console.error("Error accessing contract:", error);
      throw new Error("Contract is not accessible. Please check if it's properly deployed.");
    }

    const price = await contract.subscriptionPrice();
    console.log("Raw subscription price:", price, "Type:", typeof price);
    
    // ethers.formatEther handles BigInt conversion internally
    console.log("Subscription price:", ethers.formatEther(price), "ETH");
    
    console.log("Sending transaction to mint subscription");
    const tx = await contract.mintSubscription({
      value: price // ethers.js handles BigInt properly for transaction values
    });
    
    console.log("Transaction sent:", tx.hash);
    console.log("Waiting for confirmation");
    
    const receipt = await tx.wait();
    console.log("Transaction confirmed:", receipt.hash);
    
    // Return the receipt with the transaction hash
    return {
      hash: receipt.hash,
      receipt: receipt
    };
  } catch (error) {
    console.error("Error subscribing:", error);
    throw error;
  }
}; 
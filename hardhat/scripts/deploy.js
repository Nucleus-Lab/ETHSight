const { ethers } = require("hardhat");

async function main() {
  console.log("Deploying SubscriptionNFT contract...");
  
  // Deploy the contract
  const subscriptionNFT = await ethers.deployContract("SubscriptionNFT");
  await subscriptionNFT.waitForDeployment();
  
  const address = await subscriptionNFT.getAddress();
  
  console.log("SubscriptionNFT deployed to:", address);

  // For testing purposes, let's verify the contract is working
  console.log("\nTesting contract functionality:");
  
  // Get subscription price
  const price = await subscriptionNFT.subscriptionPrice();
  console.log("Subscription price:", ethers.formatEther(price), "ETH");

  // Get contract owner
  const owner = await subscriptionNFT.owner();
  console.log("Contract owner:", owner);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

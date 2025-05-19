const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");
const { loadFixture } = require("@nomicfoundation/hardhat-network-helpers");

describe("SubscriptionNFT", function () {
  async function deployFixture() {
    // Get the signers
    const [owner, otherAccount] = await ethers.getSigners();

    // Deploy the contract
    const SubscriptionNFT = await ethers.getContractFactory("SubscriptionNFT");
    const subscriptionNFT = await SubscriptionNFT.deploy();

    return { subscriptionNFT, owner, otherAccount };
  }

  let SubscriptionNFT;
  let subscriptionNFT;
  let owner;
  let user1;
  let user2;
  const SUBSCRIPTION_DURATION = 30 * 24 * 60 * 60; // 30 days in seconds

  beforeEach(async function () {
    // Get signers
    [owner, user1, user2] = await ethers.getSigners();

    // Deploy contract
    SubscriptionNFT = await ethers.getContractFactory("SubscriptionNFT");
    subscriptionNFT = await SubscriptionNFT.deploy();
  });

  describe("Deployment", function () {
    it("Should set the right owner", async function () {
      const { subscriptionNFT, owner } = await loadFixture(deployFixture);
      expect(await subscriptionNFT.owner()).to.equal(owner.address);
    });

    it("Should set the correct subscription price", async function () {
      const { subscriptionNFT } = await loadFixture(deployFixture);
      const price = await subscriptionNFT.subscriptionPrice();
      expect(price).to.equal(ethers.parseEther("0.0001")); // 0.0001 BNB
    });
  });

  describe("Subscription Management", function () {
    it("Should allow a user to mint a subscription NFT", async function () {
      const { subscriptionNFT, otherAccount } = await loadFixture(deployFixture);
      const subscriptionPrice = await subscriptionNFT.subscriptionPrice();
      
      await expect(subscriptionNFT.connect(otherAccount).mintSubscription({ value: subscriptionPrice }))
        .to.emit(subscriptionNFT, "Transfer")
        .withArgs(ethers.ZeroAddress, otherAccount.address, 1);
      
      expect(await subscriptionNFT.ownerOf(0)).to.equal(otherAccount.address);
    });

    it("Should fail if payment is insufficient", async function () {
      const { subscriptionNFT, otherAccount } = await loadFixture(deployFixture);
      const insufficientAmount = ethers.parseEther("0.00005"); // Half the price
      
      await expect(
        subscriptionNFT.connect(otherAccount).mintSubscription({ value: insufficientAmount })
      ).to.be.revertedWith("Insufficient payment");
    });

    it("Should correctly track subscription expiry", async function () {
      const { subscriptionNFT, otherAccount } = await loadFixture(deployFixture);
      const subscriptionPrice = await subscriptionNFT.subscriptionPrice();
      
      // Mint a subscription NFT
      await subscriptionNFT.connect(otherAccount).mintSubscription({ value: subscriptionPrice });
      
      // Get the expiry time
      const expiryTime = await subscriptionNFT.getSubscriptionExpiry(0);
      const currentTime = await time.latest();
      
      // Convert both times to BigNumber for comparison
      expect(expiryTime).to.be.gt(BigInt(currentTime));
      expect(expiryTime).to.be.equal(BigInt(currentTime) + BigInt(30 * 24 * 60 * 60));
    });

    it("Should correctly return user's valid subscription", async function () {
      const { subscriptionNFT, otherAccount } = await loadFixture(deployFixture);
      const subscriptionPrice = await subscriptionNFT.subscriptionPrice();
      
      // Initially should have no valid subscription
      const tokenId1 = await subscriptionNFT.getUserSubscription(otherAccount.address);
      expect(tokenId1).to.equal(0);

      // Mint a subscription NFT
      await subscriptionNFT.connect(otherAccount).mintSubscription({ value: subscriptionPrice });
      
      // Should now have a valid subscription
      const tokenId2 = await subscriptionNFT.getUserSubscription(otherAccount.address);
      expect(tokenId2).to.equal(1);

      // Fast forward past expiry
      const expiryTime = await subscriptionNFT.getSubscriptionExpiry(1);
      await time.increaseTo(expiryTime + BigInt(1));
      
      // Should no longer have a valid subscription
      const tokenId3 = await subscriptionNFT.getUserSubscription(otherAccount.address);
      expect(tokenId3).to.equal(0);
    });
  });
}); 
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract SubscriptionNFT is ERC721, Ownable {
    // Counter for token IDs, start from 1 (0 reserved for "no subscription")
    uint256 private _nextTokenId = 1;

    // Mapping from token ID to expiry timestamp
    mapping(uint256 => uint256) public tokenExpiry;
    
    // Subscription price in BNB
    uint256 public subscriptionPrice = 0.0001 ether;
    
    // Subscription duration in seconds (30 days)
    uint256 public constant SUBSCRIPTION_DURATION = 30 days;

    constructor() ERC721("DataViz Subscription", "DVSUB") Ownable(msg.sender) {}

    function mintSubscription() public payable {
        require(msg.value >= subscriptionPrice, "Insufficient payment");
        
        // Refund excess payment
        if (msg.value > subscriptionPrice) {
            payable(msg.sender).transfer(msg.value - subscriptionPrice);
        }

        uint256 tokenId = _nextTokenId++;
        
        // Mint NFT to sender
        _safeMint(msg.sender, tokenId);
        
        // Set expiry date to 30 days from now
        tokenExpiry[tokenId] = block.timestamp + SUBSCRIPTION_DURATION;
    }

    function isSubscriptionValid(uint256 tokenId) public view returns (bool) {
        return tokenExpiry[tokenId] > block.timestamp;
    }

    function getSubscriptionExpiry(uint256 tokenId) public view returns (uint256) {
        return tokenExpiry[tokenId];
    }

    function getUserSubscription(address user) public view returns (uint256) {
        uint256 balance = balanceOf(user);
        if (balance == 0) return 0; // 0 means no subscription
        
        // Start checking from 1 since we're skipping 0 as a valid token ID
        for (uint256 i = 1; i < _nextTokenId; i++) {
            try this.ownerOf(i) returns (address owner) {
                if (owner == user && isSubscriptionValid(i)) {
                    return i;
                }
            } catch {
                continue;
            }
        }
        return 0; // No valid subscription found
    }

    // Function to withdraw collected fees
    function withdrawFees() public onlyOwner {
        uint256 balance = address(this).balance;
        require(balance > 0, "No fees to withdraw");
        payable(owner()).transfer(balance);
    }
} 
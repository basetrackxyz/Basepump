// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./BasePumpToken.sol";

contract BasePumpFactory {
    address public owner;
    address public constant PLATFORM_WALLET = 0xaB0f481FCaE15f76aF749b6ADb699CF5566b45b6;
    uint256 public constant DEPLOY_FEE = 0.0005 ether; // fee to create token

    struct TokenInfo {
        address tokenAddress;
        string name;
        string symbol;
        string description;
        string imageURI;
        address creator;
        uint256 createdAt;
    }

    TokenInfo[] public allTokens;
    mapping(address => address[]) public creatorTokens;
    mapping(address => bool) public isBasePumpToken;

    event TokenCreated(
        address indexed tokenAddress,
        address indexed creator,
        string name,
        string symbol
    );

    constructor() {
        owner = msg.sender;
    }

    function createToken(
        string memory _name,
        string memory _symbol,
        string memory _description,
        string memory _imageURI
    ) external payable returns (address) {
        require(msg.value >= DEPLOY_FEE, "Insufficient deploy fee");

        // Send deploy fee to platform
        payable(PLATFORM_WALLET).transfer(DEPLOY_FEE);

        // Refund excess
        if (msg.value > DEPLOY_FEE) {
            payable(msg.sender).transfer(msg.value - DEPLOY_FEE);
        }

        BasePumpToken token = new BasePumpToken(
            _name,
            _symbol,
            _description,
            _imageURI,
            msg.sender
        );

        address tokenAddr = address(token);
        isBasePumpToken[tokenAddr] = true;
        creatorTokens[msg.sender].push(tokenAddr);
        allTokens.push(TokenInfo({
            tokenAddress: tokenAddr,
            name: _name,
            symbol: _symbol,
            description: _description,
            imageURI: _imageURI,
            creator: msg.sender,
            createdAt: block.timestamp
        }));

        emit TokenCreated(tokenAddr, msg.sender, _name, _symbol);
        return tokenAddr;
    }

    function getAllTokens() external view returns (TokenInfo[] memory) {
        return allTokens;
    }

    function getCreatorTokens(address creator) external view returns (address[] memory) {
        return creatorTokens[creator];
    }

    function totalTokens() external view returns (uint256) {
        return allTokens.length;
    }
}

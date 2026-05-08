// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./BasePumpToken.sol";

contract BasePumpFactory {
        address public owner;
            address public platformWallet;

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

                                    constructor(address _platformWallet) {
                                                owner          = msg.sender;
                                                        platformWallet = _platformWallet;
                                    }

                                        function createToken(
                                                    string memory _name,
                                                            string memory _symbol,
                                                                    string memory _description,
                                                                            string memory _imageURI
                                        ) external returns (address) {
                                                    BasePumpToken token = new BasePumpToken(
                                                                    _name,
                                                                                _symbol,
                                                                                            _description,
                                                                                                        _imageURI,
                                                                                                                    msg.sender,
                                                                                                                                platformWallet
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

                                                        function updatePlatformWallet(address _new) external {
                                                                    require(msg.sender == owner, "Not owner");
                                                                            platformWallet = _new;
                                                        }
}

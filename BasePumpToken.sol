// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IUniswapV2Router02 {
    function addLiquidityETH(
        address token,
        uint amountTokenDesired,
        uint amountTokenMin,
        uint amountETHMin,
        address to,
        uint deadline
    ) external payable returns (uint amountToken, uint amountETH, uint liquidity);
}

contract BasePumpToken {
    string public name;
    string public symbol;
    uint8 public constant decimals = 18;
    string public description;
    string public imageURI;
    address public creator;
    address public factory;
    address public platformWallet;

    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    uint256 public constant MAX_SUPPLY       = 1_000_000_000 * 1e18;
    uint256 public constant MIGRATE_SUPPLY   = 800_000_000 * 1e18;
    uint256 public constant K                = 4e9;
    uint256 public constant SCALE            = 1e18;
    uint256 public constant PLATFORM_FEE_BPS = 100;
    uint256 public constant CREATOR_FEE_BPS  = 50;
    uint256 public constant BPS              = 10000;

    address public constant UNISWAP_ROUTER   = 0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24;

    bool public migrated = false;
    uint256 public ethCollected;

    event TokensBought(address indexed buyer, uint256 ethIn, uint256 tokensOut);
    event TokensSold(address indexed seller, uint256 tokensIn, uint256 ethOut);
    event Migrated(uint256 ethAmount, uint256 tokenAmount);

    modifier notMigrated() {
        require(!migrated, "Token has graduated to DEX");
        _;
    }

    constructor(
        string memory _name,
        string memory _symbol,
        string memory _description,
        string memory _imageURI,
        address _creator,
        address _platformWallet
    ) {
        name           = _name;
        symbol         = _symbol;
        description    = _description;
        imageURI       = _imageURI;
        creator        = _creator;
        factory        = msg.sender;
        platformWallet = _platformWallet;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(allowance[from][msg.sender] >= amount, "Allowance exceeded");
        allowance[from][msg.sender] -= amount;
        _transfer(from, to, amount);
        return true;
    }

    function _transfer(address from, address to, uint256 amount) internal {
        require(balanceOf[from] >= amount, "Insufficient balance");
        balanceOf[from] -= amount;
        balanceOf[to]   += amount;
        emit Transfer(from, to, amount);
    }

    function _mint(address to, uint256 amount) internal {
        totalSupply   += amount;
        balanceOf[to] += amount;
        emit Transfer(address(0), to, amount);
    }

    function _burn(address from, uint256 amount) internal {
        require(balanceOf[from] >= amount, "Insufficient balance");
        totalSupply    -= amount;
        balanceOf[from] -= amount;
        emit Transfer(from, address(0), amount);
    }

    function getBuyPrice(uint256 tokenAmount) public view returns (uint256 ethRequired) {
        uint256 s = totalSupply;
        uint256 newSupply = s + tokenAmount;
        ethRequired = K * (newSupply * newSupply - s * s) / (2 * SCALE * SCALE);
    }

    function getSellPrice(uint256 tokenAmount) public view returns (uint256 ethOut) {
        uint256 s = totalSupply;
        require(s >= tokenAmount, "Exceeds supply");
        uint256 newSupply = s - tokenAmount;
        ethOut = K * (s * s - newSupply * newSupply) / (2 * SCALE * SCALE);
    }

    function getTokensForETH(uint256 ethAmount) public view returns (uint256 tokenAmount) {
        uint256 s = totalSupply;
        uint256 inner = s * s + (2 * ethAmount * SCALE * SCALE) / K;
        tokenAmount = sqrt(inner) - s;
    }

    function buy() external payable notMigrated {
        require(msg.value > 0, "Send ETH to buy");
        uint256 platformFee = (msg.value * PLATFORM_FEE_BPS) / BPS;
        uint256 creatorFee  = (msg.value * CREATOR_FEE_BPS) / BPS;
        uint256 ethIn       = msg.value - platformFee - creatorFee;
        uint256 tokenAmount = getTokensForETH(ethIn);
        require(totalSupply + tokenAmount <= MAX_SUPPLY, "Exceeds max supply");

        (bool p,) = platformWallet.call{value: platformFee}("");
        require(p, "Platform fee failed");
        (bool c,) = creator.call{value: creatorFee}("");
        require(c, "Creator fee failed");

        ethCollected += ethIn;
        _mint(msg.sender, tokenAmount);
        emit TokensBought(msg.sender, ethIn, tokenAmount);

        if (totalSupply >= MIGRATE_SUPPLY) {
            _migrate();
        }
    }

    function sell(uint256 tokenAmount) external notMigrated {
        require(tokenAmount > 0, "Amount must be > 0");
        require(balanceOf[msg.sender] >= tokenAmount, "Insufficient tokens");
        uint256 ethOut      = getSellPrice(tokenAmount);
        uint256 platformFee = (ethOut * PLATFORM_FEE_BPS) / BPS;
        uint256 creatorFee  = (ethOut * CREATOR_FEE_BPS) / BPS;
        uint256 ethToSender = ethOut - platformFee - creatorFee;
        require(address(this).balance >= ethOut, "Insufficient liquidity");

        _burn(msg.sender, tokenAmount);
        ethCollected -= ethOut;

        (bool p,) = platformWallet.call{value: platformFee}("");
        require(p, "Platform fee failed");
        (bool c,) = creator.call{value: creatorFee}("");
        require(c, "Creator fee failed");
        (bool s,) = msg.sender.call{value: ethToSender}("");
        require(s, "Transfer failed");

        emit TokensSold(msg.sender, tokenAmount, ethToSender);
    }

    function _migrate() internal {
        migrated = true;
        uint256 remainingTokens = MAX_SUPPLY - totalSupply;
        uint256 ethForLiquidity = address(this).balance;
        _mint(address(this), remainingTokens);
        allowance[address(this)][UNISWAP_ROUTER] = remainingTokens;
        IUniswapV2Router02(UNISWAP_ROUTER).addLiquidityETH{value: ethForLiquidity}(
            address(this),
            remainingTokens,
            0,
            0,
            address(0),
            block.timestamp + 300
        );
        emit Migrated(ethForLiquidity, remainingTokens);
    }

    function sqrt(uint256 x) internal pure returns (uint256 y) {
        if (x == 0) return 0;
        uint256 z = (x + 1) / 2;
        y = x;
        while (z < y) {
            y = z;
            z = (x / z + z) / 2;
        }
    }

    receive() external payable {}
}

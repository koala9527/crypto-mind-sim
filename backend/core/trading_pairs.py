"""主流交易对配置。"""

POPULAR_TRADING_PAIRS = [
    {"symbol": "BTC/USDT", "name": "比特币", "description": "Bitcoin"},
    {"symbol": "ETH/USDT", "name": "以太坊", "description": "Ethereum"},
    {"symbol": "SOL/USDT", "name": "Solana", "description": "Solana"},
    {"symbol": "XRP/USDT", "name": "瑞波币", "description": "XRP"},
    {"symbol": "DOGE/USDT", "name": "狗狗币", "description": "Dogecoin"},
    {"symbol": "BNB/USDT", "name": "币安币", "description": "BNB"},
    {"symbol": "ADA/USDT", "name": "艾达币", "description": "Cardano"},
    {"symbol": "LINK/USDT", "name": "链环", "description": "Chainlink"},
    {"symbol": "TRX/USDT", "name": "波场", "description": "TRON"},
    {"symbol": "SHIB/USDT", "name": "柴犬币", "description": "Shiba Inu"},
]

DEFAULT_SYMBOL = POPULAR_TRADING_PAIRS[0]["symbol"]
MARKET_OVERVIEW_SYMBOLS = [pair["symbol"] for pair in POPULAR_TRADING_PAIRS[:5]]
POPULAR_SYMBOL_CODES = [pair["symbol"] for pair in POPULAR_TRADING_PAIRS]

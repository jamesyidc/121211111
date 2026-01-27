"""
Test different TradingView symbol formats for OKEx
"""
from tradingview_ta import TA_Handler, Interval

# Test different symbol formats
test_configs = [
    {"symbol": "UNIUSDTPERP", "exchange": "OKX", "name": "UNI USDT PERP"},
    {"symbol": "UNIUSDT.P", "exchange": "OKX", "name": "UNI USDT .P"},
    {"symbol": "UNI-USDT-SWAP", "exchange": "OKX", "name": "UNI-USDT-SWAP"},
    {"symbol": "UNIUSDT", "exchange": "OKEX", "name": "UNI USDT on OKEX"},
    {"symbol": "UNIUSDTPERP", "exchange": "OKEX", "name": "UNI USDT PERP on OKEX"},
    {"symbol": "BTCUSDTPERP", "exchange": "OKX", "name": "BTC USDT PERP"},
    {"symbol": "BTCUSDT.P", "exchange": "OKX", "name": "BTC USDT .P"},
]

print("Testing different OKEx symbol formats on TradingView...\n")

for config in test_configs:
    try:
        handler = TA_Handler(
            symbol=config["symbol"],
            exchange=config["exchange"],
            screener="crypto",
            interval=Interval.INTERVAL_5_MINUTES
        )
        analysis = handler.get_analysis()
        indicators = analysis.indicators
        
        print(f"✅ SUCCESS: {config['name']}")
        print(f"   Exchange: {config['exchange']}, Symbol: {config['symbol']}")
        print(f"   Price: ${indicators.get('close', 'N/A')}")
        print(f"   RSI(14): {indicators.get('RSI', 'N/A')}")
        print(f"   BB Upper: {indicators.get('BB.upper', 'N/A')}")
        print()
        
    except Exception as e:
        print(f"❌ FAILED: {config['name']} - {str(e)}")


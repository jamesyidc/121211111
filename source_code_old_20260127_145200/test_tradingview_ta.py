"""
Test using tradingview-ta library to directly fetch technical indicators
This library fetches real-time technical analysis from TradingView
"""
import sys
import json
from datetime import datetime

try:
    from tradingview_ta import TA_Handler, Interval, Exchange
    print("✅ tradingview_ta library is available")
except ImportError:
    print("❌ tradingview_ta not installed, installing now...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tradingview-ta"])
    from tradingview_ta import TA_Handler, Interval, Exchange
    print("✅ tradingview_ta installed successfully")

def get_okex_indicators(symbol, timeframe='5m'):
    """
    直接从 TradingView 获取 OKEx 的技术指标
    不进行本地计算，直接读取 TradingView 的分析结果
    """
    # Convert symbol format: BTC-USDT-SWAP -> BTCUSDTPERP
    base_symbol = symbol.replace('-USDT-SWAP', '')
    tv_symbol = f"{base_symbol}USDTPERP"
    
    # Convert timeframe
    interval_map = {
        '5m': Interval.INTERVAL_5_MINUTES,
        '1h': Interval.INTERVAL_1_HOUR,
    }
    
    try:
        handler = TA_Handler(
            symbol=tv_symbol,
            exchange="OKX",  # OKEx exchange
            screener="crypto",
            interval=interval_map.get(timeframe, Interval.INTERVAL_5_MINUTES)
        )
        
        # 直接获取分析结果
        analysis = handler.get_analysis()
        
        print(f"\n{'='*60}")
        print(f"Symbol: {symbol} ({tv_symbol})")
        print(f"Timeframe: {timeframe}")
        print(f"Data Source: TradingView (OKX Exchange)")
        print(f"Fetch Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        # 获取技术指标 - 直接从 TradingView 读取，不计算
        indicators = analysis.indicators
        
        print(f"\n📊 直接获取的技术指标:")
        print(f"Current Price: ${indicators.get('close', 'N/A')}")
        print(f"\n🔴 RSI (Relative Strength Index):")
        print(f"  RSI(14): {indicators.get('RSI', 'N/A')}")
        
        print(f"\n🟢 Bollinger Bands:")
        print(f"  Upper Band (UB): {indicators.get('BB.upper', 'N/A')}")
        print(f"  Middle Band (BOLL): {indicators.get('BB.middle', 'N/A')}")  
        print(f"  Lower Band (LB): {indicators.get('BB.lower', 'N/A')}")
        
        # TradingView 提供的其他重要指标
        print(f"\n🔵 Other Indicators:")
        print(f"  EMA(10): {indicators.get('EMA10', 'N/A')}")
        print(f"  EMA(20): {indicators.get('EMA20', 'N/A')}")
        print(f"  SMA(10): {indicators.get('SMA10', 'N/A')}")
        print(f"  SMA(20): {indicators.get('SMA20', 'N/A')}")
        
        # 综合建议
        print(f"\n📈 TradingView Recommendation:")
        print(f"  Summary: {analysis.summary.get('RECOMMENDATION', 'N/A')}")
        print(f"  Buy: {analysis.summary.get('BUY', 0)}")
        print(f"  Sell: {analysis.summary.get('SELL', 0)}")
        print(f"  Neutral: {analysis.summary.get('NEUTRAL', 0)}")
        
        # 返回结构化数据
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'current_price': indicators.get('close'),
            'rsi_14': indicators.get('RSI'),
            'bb_upper': indicators.get('BB.upper'),
            'bb_middle': indicators.get('BB.middle'),
            'bb_lower': indicators.get('BB.lower'),
            'ema_10': indicators.get('EMA10'),
            'ema_20': indicators.get('EMA20'),
            'recommendation': analysis.summary.get('RECOMMENDATION'),
            'fetch_time': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Error fetching data for {symbol}: {str(e)}")
        return None

if __name__ == "__main__":
    # 测试 UNI
    print("\n" + "="*70)
    print("Testing Direct Technical Indicator Fetching from TradingView")
    print("="*70)
    
    result = get_okex_indicators('UNI-USDT-SWAP', '5m')
    
    if result:
        print(f"\n✅ Successfully fetched indicators directly from TradingView")
        print(f"\n返回的JSON数据:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"\n❌ Failed to fetch indicators")


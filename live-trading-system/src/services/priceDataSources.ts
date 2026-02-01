/**
 * 多数据源价格获取服务
 * 支持自动故障切换：CoinGecko -> Binance -> CoinMarketCap -> Kraken
 */

interface PriceData {
  symbol: string;
  price: number;
  change_24h: number;
  volume_24h?: number;
  market_cap?: number;
  source: string;
}

interface DataSourceResult {
  success: boolean;
  data?: PriceData[];
  error?: string;
  source: string;
}

/**
 * 数据源 1: Binance API（主备份）
 * 优点: 速率限制高(1200/分钟)，实时性强，无需API密钥
 */
async function fetchFromBinance(symbols: string[]): Promise<DataSourceResult> {
  try {
    console.log('🔄 尝试从 Binance 获取数据...');
    
    const results: PriceData[] = [];
    
    // Binance API 需要逐个查询或批量查询ticker
    const tickerUrl = 'https://api.binance.com/api/v3/ticker/24hr';
    const response = await fetch(tickerUrl);
    
    if (!response.ok) {
      throw new Error(`Binance API error: ${response.status}`);
    }
    
    const allTickers = await response.json();
    
    // 过滤出我们需要的币种
    for (const symbol of symbols) {
      const binanceSymbol = `${symbol}USDT`;
      const ticker = allTickers.find((t: any) => t.symbol === binanceSymbol);
      
      if (ticker) {
        results.push({
          symbol,
          price: parseFloat(ticker.lastPrice),
          change_24h: parseFloat(ticker.priceChangePercent),
          volume_24h: parseFloat(ticker.volume) * parseFloat(ticker.lastPrice),
          source: 'Binance'
        });
      }
    }
    
    if (results.length === 0) {
      throw new Error('No data from Binance');
    }
    
    console.log(`✅ Binance 成功: ${results.length}/${symbols.length} 币种`);
    return {
      success: true,
      data: results,
      source: 'Binance'
    };
  } catch (error: any) {
    console.error('❌ Binance 失败:', error.message);
    return {
      success: false,
      error: error.message,
      source: 'Binance'
    };
  }
}

/**
 * 数据源 2: CoinMarketCap API（次备份）
 * 优点: 数据权威，更新快
 * 注意: 需要API密钥，免费版333次/天
 */
async function fetchFromCoinMarketCap(symbols: string[], apiKey?: string): Promise<DataSourceResult> {
  try {
    console.log('🔄 尝试从 CoinMarketCap 获取数据...');
    
    if (!apiKey) {
      throw new Error('CoinMarketCap API key not configured');
    }
    
    const symbolList = symbols.join(',');
    const url = `https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol=${symbolList}&convert=USD`;
    
    const response = await fetch(url, {
      headers: {
        'X-CMC_PRO_API_KEY': apiKey,
        'Accept': 'application/json'
      }
    });
    
    if (!response.ok) {
      throw new Error(`CoinMarketCap API error: ${response.status}`);
    }
    
    const json = await response.json();
    const results: PriceData[] = [];
    
    for (const symbol of symbols) {
      const data = json.data[symbol];
      if (data) {
        const quote = data.quote.USD;
        results.push({
          symbol,
          price: quote.price,
          change_24h: quote.percent_change_24h,
          volume_24h: quote.volume_24h,
          market_cap: quote.market_cap,
          source: 'CoinMarketCap'
        });
      }
    }
    
    if (results.length === 0) {
      throw new Error('No data from CoinMarketCap');
    }
    
    console.log(`✅ CoinMarketCap 成功: ${results.length}/${symbols.length} 币种`);
    return {
      success: true,
      data: results,
      source: 'CoinMarketCap'
    };
  } catch (error: any) {
    console.error('❌ CoinMarketCap 失败:', error.message);
    return {
      success: false,
      error: error.message,
      source: 'CoinMarketCap'
    };
  }
}

/**
 * 数据源 3: Kraken API（最终备份）
 * 优点: 稳定可靠，速率限制15次/秒
 */
async function fetchFromKraken(symbols: string[]): Promise<DataSourceResult> {
  try {
    console.log('🔄 尝试从 Kraken 获取数据...');
    
    const results: PriceData[] = [];
    
    // Kraken 使用不同的交易对命名
    const krakenSymbolMap: Record<string, string> = {
      'BTC': 'XXBTZUSD',
      'ETH': 'XETHZUSD',
      'XRP': 'XXRPZUSD',
      'SOL': 'SOLUSD',
      'LTC': 'XLTCZUSD',
      'DOGE': 'XDGUSD',
      'ADA': 'ADAUSD',
      'DOT': 'DOTUSD',
      'LINK': 'LINKUSD'
    };
    
    // 批量查询ticker信息
    const krakenPairs = symbols
      .filter(s => krakenSymbolMap[s])
      .map(s => krakenSymbolMap[s])
      .join(',');
    
    if (!krakenPairs) {
      throw new Error('No supported symbols for Kraken');
    }
    
    const url = `https://api.kraken.com/0/public/Ticker?pair=${krakenPairs}`;
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`Kraken API error: ${response.status}`);
    }
    
    const json = await response.json();
    
    if (json.error && json.error.length > 0) {
      throw new Error(`Kraken error: ${json.error.join(', ')}`);
    }
    
    for (const symbol of symbols) {
      const krakenSymbol = krakenSymbolMap[symbol];
      if (krakenSymbol && json.result[krakenSymbol]) {
        const ticker = json.result[krakenSymbol];
        const price = parseFloat(ticker.c[0]);
        const open = parseFloat(ticker.o);
        const change_24h = ((price - open) / open) * 100;
        
        results.push({
          symbol,
          price,
          change_24h,
          volume_24h: parseFloat(ticker.v[1]) * price,
          source: 'Kraken'
        });
      }
    }
    
    if (results.length === 0) {
      throw new Error('No data from Kraken');
    }
    
    console.log(`✅ Kraken 成功: ${results.length}/${symbols.length} 币种`);
    return {
      success: true,
      data: results,
      source: 'Kraken'
    };
  } catch (error: any) {
    console.error('❌ Kraken 失败:', error.message);
    return {
      success: false,
      error: error.message,
      source: 'Kraken'
    };
  }
}

/**
 * 数据源 4: CoinGecko API（原有数据源）
 */
async function fetchFromCoinGecko(symbols: string[], symbolToIdMap: Record<string, string>): Promise<DataSourceResult> {
  try {
    console.log('🔄 尝试从 CoinGecko 获取数据...');
    
    const ids = symbols
      .map(symbol => symbolToIdMap[symbol])
      .filter(id => id)
      .join(',');
    
    if (!ids) {
      throw new Error('No CoinGecko IDs available');
    }
    
    const url = `https://api.coingecko.com/api/v3/simple/price?ids=${ids}&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true&include_market_cap=true`;
    
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`CoinGecko API error: ${response.status}`);
    }
    
    const data = await response.json();
    const results: PriceData[] = [];
    
    for (const symbol of symbols) {
      const coinId = symbolToIdMap[symbol];
      if (coinId && data[coinId]) {
        const coinData = data[coinId];
        results.push({
          symbol,
          price: coinData.usd,
          change_24h: coinData.usd_24h_change || 0,
          volume_24h: coinData.usd_24h_vol,
          market_cap: coinData.usd_market_cap,
          source: 'CoinGecko'
        });
      }
    }
    
    if (results.length === 0) {
      throw new Error('No data from CoinGecko');
    }
    
    console.log(`✅ CoinGecko 成功: ${results.length}/${symbols.length} 币种`);
    return {
      success: true,
      data: results,
      source: 'CoinGecko'
    };
  } catch (error: any) {
    console.error('❌ CoinGecko 失败:', error.message);
    return {
      success: false,
      error: error.message,
      source: 'CoinGecko'
    };
  }
}

/**
 * 主函数：自动故障切换获取价格数据
 * 优先级: CoinGecko -> Binance -> CoinMarketCap -> Kraken
 */
export async function fetchPriceDataWithFallback(
  symbols: string[],
  symbolToIdMap: Record<string, string>,
  cmcApiKey?: string
): Promise<DataSourceResult> {
  console.log(`\n📊 开始获取 ${symbols.length} 个币种的价格数据...`);
  console.log(`🔄 尝试顺序: CoinGecko -> Binance -> CoinMarketCap -> Kraken\n`);
  
  // 1. 尝试 CoinGecko（原有数据源）
  let result = await fetchFromCoinGecko(symbols, symbolToIdMap);
  if (result.success) {
    return result;
  }
  
  // 2. 尝试 Binance（主备份）
  console.log('\n⚠️ CoinGecko 失败，切换到 Binance...');
  result = await fetchFromBinance(symbols);
  if (result.success) {
    return result;
  }
  
  // 3. 尝试 CoinMarketCap（次备份，如果配置了API密钥）
  if (cmcApiKey) {
    console.log('\n⚠️ Binance 失败，切换到 CoinMarketCap...');
    result = await fetchFromCoinMarketCap(symbols, cmcApiKey);
    if (result.success) {
      return result;
    }
  }
  
  // 4. 尝试 Kraken（最终备份）
  console.log('\n⚠️ 前置数据源失败，切换到 Kraken...');
  result = await fetchFromKraken(symbols);
  if (result.success) {
    return result;
  }
  
  // 所有数据源都失败
  console.error('\n❌ 所有数据源均失败！');
  return {
    success: false,
    error: 'All data sources failed',
    source: 'None'
  };
}

export type { PriceData, DataSourceResult };

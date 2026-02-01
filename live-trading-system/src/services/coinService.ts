import type { Bindings, CoinGeckoSimplePrice } from '../types';
import { getBeijingDateString, getBeijingYesterday, getBeijingTodayStart, convertUTCtoBeijingDateString } from '../utils/timeUtils';

// 币种符号到 CoinGecko ID 的映射
const SYMBOL_TO_COINGECKO_ID: Record<string, string> = {
  'BTC': 'bitcoin',
  'ETH': 'ethereum',
  'XRP': 'ripple',
  'BNB': 'binancecoin',
  'SOL': 'solana',
  'LTC': 'litecoin',
  'DOGE': 'dogecoin',
  'SUI': 'sui',
  'TRX': 'tron',
  'TON': 'the-open-network',
  'ETC': 'ethereum-classic',
  'BCH': 'bitcoin-cash',
  'HBAR': 'hedera-hashgraph',
  'XLM': 'stellar',
  'FIL': 'filecoin',
  'ADA': 'cardano',
  'LINK': 'chainlink',
  'CRO': 'crypto-com-chain',
  'DOT': 'polkadot',
  'OKB': 'okb',
  'AAVE': 'aave',
  'UNI': 'uniswap',
  'NEAR': 'near',
  'APT': 'aptos',
  'CFX': 'conflux-token',
  'CRV': 'curve-dao-token',
  'STX': 'blockstack',
  'LDO': 'lido-dao',
  'TAO': 'bittensor'
};

export class CoinService {
  private db: D1Database;

  constructor(db: D1Database) {
    this.db = db;
  }

  // 获取所有币种
  async getAllCoins() {
    const result = await this.db
      .prepare(`
        SELECT c.*, p.level
        FROM coins c
        LEFT JOIN coin_priority p ON c.symbol = p.symbol
        ORDER BY c.rank_order
      `)
      .all();
    return result.results;
  }

  // 从 CoinGecko 获取价格数据（带重试和指数退避）
  async fetchPricesFromCoinGecko(): Promise<CoinGeckoSimplePrice> {
    const coins = await this.getAllCoins();
    const ids = coins.map((c: any) => SYMBOL_TO_COINGECKO_ID[c.symbol]).join(',');
    
    const url = `https://api.coingecko.com/api/v3/simple/price?ids=${ids}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true&include_24hr_vol=true`;
    
    // 重试配置：最多重试3次，使用指数退避
    const maxRetries = 3;
    let lastError: Error | null = null;
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        // 如果不是第一次尝试，等待一段时间（指数退避）
        if (attempt > 0) {
          const waitTime = Math.min(1000 * Math.pow(2, attempt - 1), 10000); // 1s, 2s, 4s，最多10s
          console.log(`CoinGecko API 重试 ${attempt}/${maxRetries}，等待 ${waitTime}ms...`);
          await new Promise(resolve => setTimeout(resolve, waitTime));
        }
        
        const response = await fetch(url, {
          headers: {
            'Accept': 'application/json',
          }
        });

        // 429 错误（限流）- 继续重试
        if (response.status === 429) {
          console.warn(`CoinGecko API 限流 (429)，尝试 ${attempt + 1}/${maxRetries + 1}`);
          lastError = new Error(`CoinGecko API 限流: ${response.status}`);
          continue;
        }

        // 其他错误 - 不重试，直接抛出
        if (!response.ok) {
          throw new Error(`CoinGecko API error: ${response.status}`);
        }

        // 成功获取数据
        return await response.json();
        
      } catch (error: any) {
        console.error(`CoinGecko API 请求失败 (尝试 ${attempt + 1}/${maxRetries + 1}):`, error.message);
        lastError = error;
        
        // 如果是最后一次尝试，抛出错误
        if (attempt === maxRetries) {
          throw error;
        }
      }
    }
    
    // 如果所有重试都失败，尝试使用备份数据源
    console.error('CoinGecko API 所有重试均失败，尝试使用备份数据源...');
    
    // 尝试 Binance API
    try {
      return await this.fetchPricesFromBinance();
    } catch (binanceError: any) {
      console.error('Binance 备份数据源失败:', binanceError.message);
    }
    
    // 尝试 CryptoCompare API 作为第三备份
    try {
      console.log('尝试 CryptoCompare API 作为第三备份数据源...');
      return await this.fetchPricesFromCoinCap();
    } catch (cryptocompareError: any) {
      console.error('CryptoCompare 备份数据源也失败:', cryptocompareError.message);
    }
    
    throw lastError || new Error('所有数据源均请求失败（CoinGecko + Binance + CryptoCompare）');
  }
  
  // 从 CryptoCompare 获取价格数据（第三备份数据源）
  private async fetchPricesFromCoinCap(): Promise<CoinGeckoSimplePrice> {
    const coins = await this.getAllCoins();
    const result: CoinGeckoSimplePrice = {};
    
    console.log('使用 CryptoCompare API 作为第三备份数据源...');
    
    // 将所有币种符号组合成批量请求
    const symbols = coins.map((c: any) => c.symbol).join(',');
    
    try {
      // CryptoCompare 支持批量查询
      const url = `https://min-api.cryptocompare.com/data/pricemultifull?fsyms=${symbols}&tsyms=USD`;
      const response = await fetch(url, {
        headers: { 'Accept': 'application/json' }
      });
      
      if (!response.ok) {
        throw new Error(`CryptoCompare API error: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (!data.RAW) {
        throw new Error('CryptoCompare API 返回数据格式错误');
      }
      
      // 转换为 CoinGecko 格式
      for (const coin of coins) {
        const symbol = coin.symbol;
        const coinData = data.RAW[symbol]?.USD;
        
        if (coinData) {
          const coinGeckoId = SYMBOL_TO_COINGECKO_ID[symbol];
          result[coinGeckoId] = {
            usd: coinData.PRICE,
            usd_24h_change: coinData.CHANGEPCT24HOUR,
            usd_market_cap: coinData.MKTCAP,
            usd_24h_vol: coinData.VOLUME24HOURTO
          };
        } else {
          console.warn(`CryptoCompare: 未找到 ${symbol} 的数据`);
        }
      }
      
      const successCount = Object.keys(result).length;
      if (successCount < coins.length / 2) {
        throw new Error(`CryptoCompare API 数据不足: 仅获取到 ${successCount}/${coins.length} 个币种`);
      }
      
      console.log(`✅ CryptoCompare API 成功获取 ${successCount}/${coins.length} 个币种的数据`);
      return result;
      
    } catch (error: any) {
      console.error('CryptoCompare API 请求失败:', error.message);
      throw error;
    }
  }
  
  // 从 Binance 获取价格数据（备份数据源）
  private async fetchPricesFromBinance(): Promise<CoinGeckoSimplePrice> {
    const coins = await this.getAllCoins();
    const result: CoinGeckoSimplePrice = {};
    
    console.log('使用 Binance API 作为备份数据源...');
    
    // Binance API 需要单独请求每个币种
    // 为了简化，我们只获取价格，不获取24h变化
    for (const coin of coins) {
      const symbol = coin.symbol;
      const pair = `${symbol}USDT`;
      
      try {
        // Binance 24hr ticker API
        const url = `https://api.binance.com/api/v3/ticker/24hr?symbol=${pair}`;
        const response = await fetch(url);
        
        if (response.ok) {
          const data = await response.json();
          const coinGeckoId = SYMBOL_TO_COINGECKO_ID[symbol];
          
          result[coinGeckoId] = {
            usd: parseFloat(data.lastPrice),
            usd_24h_change: parseFloat(data.priceChangePercent),
            usd_market_cap: 0, // Binance API 不提供市值
            usd_24h_vol: parseFloat(data.quoteVolume)
          };
        } else {
          console.warn(`Binance API 获取 ${symbol} 失败: ${response.status}`);
        }
        
        // 添加小延迟避免被限流
        await new Promise(resolve => setTimeout(resolve, 100));
      } catch (error: any) {
        console.warn(`Binance API 请求 ${symbol} 异常:`, error.message);
      }
    }
    
    // 检查是否获取到足够的数据
    const successCount = Object.keys(result).length;
    if (successCount < coins.length / 2) {
      throw new Error(`Binance API 数据不足: 仅获取到 ${successCount}/${coins.length} 个币种`);
    }
    
    console.log(`✅ Binance API 成功获取 ${successCount}/${coins.length} 个币种的数据`);
    return result;
  }

  // 保存价格记录
  async savePriceRecord(symbol: string, data: any) {
    await this.db
      .prepare(`
        INSERT INTO price_records (symbol, price, change_24h, market_cap, volume_24h)
        VALUES (?, ?, ?, ?, ?)
      `)
      .bind(
        symbol,
        data.usd,
        data.usd_24h_change || null,
        data.usd_market_cap || null,
        data.usd_24h_vol || null
      )
      .run();
  }

  // 获取上一次的价格记录
  async getPreviousPriceRecord(symbol: string) {
    const result = await this.db
      .prepare(`
        SELECT * FROM price_records 
        WHERE symbol = ? 
        ORDER BY timestamp DESC 
        LIMIT 1
      `)
      .bind(symbol)
      .first();
    return result;
  }

  // 获取上一轮的币种详情（用于计算轮次涨跌幅）
  async getPreviousRoundDetail(symbol: string) {
    const result = await this.db
      .prepare(`
        SELECT * FROM coin_round_details 
        WHERE symbol = ? 
        ORDER BY round_time DESC 
        LIMIT 1 OFFSET 1
      `)
      .bind(symbol)
      .first();
    return result;
  }

  // 获取或创建极值记录
  async getOrCreatePriceExtreme(symbol: string, initialPrice: number) {
    let extreme = await this.db
      .prepare('SELECT * FROM price_extremes WHERE symbol = ?')
      .bind(symbol)
      .first();

    if (!extreme) {
      await this.db
        .prepare(`
          INSERT INTO price_extremes (symbol, all_time_high, all_time_low, ath_date, atl_date)
          VALUES (?, ?, ?, datetime('now'), datetime('now'))
        `)
        .bind(symbol, initialPrice, initialPrice)
        .run();

      extreme = await this.db
        .prepare('SELECT * FROM price_extremes WHERE symbol = ?')
        .bind(symbol)
        .first();
    }

    return extreme;
  }

  // 更新极值记录（创新高/新低时调用）
  async updatePriceExtreme(symbol: string, type: 'high' | 'low', price: number) {
    if (type === 'high') {
      await this.db
        .prepare(`
          UPDATE price_extremes 
          SET all_time_high = ?, ath_date = datetime('now'), last_updated = datetime('now'), high_count = 0
          WHERE symbol = ?
        `)
        .bind(price, symbol)
        .run();
    } else {
      await this.db
        .prepare(`
          UPDATE price_extremes 
          SET all_time_low = ?, atl_date = datetime('now'), last_updated = datetime('now'), low_count = 0
          WHERE symbol = ?
        `)
        .bind(price, symbol)
        .run();
    }
  }

  // 增加计次（未创新高/新低时调用）
  async incrementExtremeCount(symbol: string, type: 'high' | 'low') {
    if (type === 'high') {
      await this.db
        .prepare(`
          UPDATE price_extremes 
          SET high_count = high_count + 1, last_updated = datetime('now')
          WHERE symbol = ?
        `)
        .bind(symbol)
        .run();
    } else {
      await this.db
        .prepare(`
          UPDATE price_extremes 
          SET low_count = low_count + 1, last_updated = datetime('now')
          WHERE symbol = ?
        `)
        .bind(symbol)
        .run();
    }
  }

  // 保存极值记录历史
  async saveExtremeRecord(symbol: string, type: 'new_high' | 'new_low', price: number, prevExtreme: number, zeroCount: number) {
    await this.db
      .prepare(`
        INSERT INTO extreme_records (symbol, record_type, price, prev_extreme, zero_count)
        VALUES (?, ?, ?, ?, ?)
      `)
      .bind(symbol, type, price, prevExtreme, zeroCount)
      .run();
  }

  // 🆕 检查是否需要重置每日极值数据（隔天第一次刷新）- 使用北京时间
  async shouldResetDailyExtremes(): Promise<boolean> {
    // 获取 price_extremes 表中最新的 last_updated 时间
    const result: any = await this.db
      .prepare(`
        SELECT last_updated 
        FROM price_extremes 
        ORDER BY last_updated DESC 
        LIMIT 1
      `)
      .first();
    
    if (!result || !result.last_updated) {
      return false; // 没有数据，不需要重置
    }
    
    // 🔥 关键：将UTC时间转换为北京时间日期进行比较
    const lastUpdateBeijingDate = convertUTCtoBeijingDateString(result.last_updated);
    const todayBeijingDate = getBeijingDateString();
    
    console.log(`📅 检查是否需要重置: 上次更新=${lastUpdateBeijingDate}, 今天=${todayBeijingDate}`);
    
    // 如果最后更新日期（北京时间）不是今天，则需要重置
    return lastUpdateBeijingDate !== todayBeijingDate;
  }

  // 🆕 重置每日极值数据（保留all_time_high/low，清零计次）
  async resetDailyExtremes() {
    await this.db
      .prepare(`
        UPDATE price_extremes 
        SET high_count = 0, 
            low_count = 0, 
            extreme_up_count = 0, 
            extreme_down_count = 0,
            last_updated = datetime('now')
      `)
      .run();
    
    console.log('✅ 已重置每日极值数据（隔天第一次刷新）');
  }

  // 🆕 完整的每日数据清零（北京时间0点执行）
  async resetAllDailyData() {
    const todayBeijing = getBeijingDateString();
    const yesterdayBeijing = getBeijingYesterday();
    
    console.log('🔄 开始执行每日数据清零（北京时间）...');
    console.log(`   📅 今天: ${todayBeijing}`);
    console.log(`   📅 昨天: ${yesterdayBeijing}`);
    
    // 🔥 关键：只清零累计计数器，不删除任何历史数据
    
    // 1. 清零极值计次数据（保留历史极值记录 all_time_high/low）
    await this.db
      .prepare(`
        UPDATE price_extremes 
        SET high_count = 0, 
            low_count = 0, 
            extreme_up_count = 0, 
            extreme_down_count = 0,
            last_updated = datetime('now')
      `)
      .run();
    console.log('  ✅ 已清零 price_extremes 计数器（创新高/低计次）');
    
    // 2. 🔥 删除今天的 daily_stats 数据（让它重新从0开始累计）
    await this.db
      .prepare(`DELETE FROM daily_stats WHERE date = ?`)
      .bind(todayBeijing)
      .run();
    console.log(`  ✅ 已清理今天的 daily_stats 数据（${todayBeijing}），重新开始累计`);
    
    // 🆕 3. 删除今天的 daily_risk_alerts 数据（清零风险提示累计）
    await this.db
      .prepare(`DELETE FROM daily_risk_alerts WHERE date = ?`)
      .bind(todayBeijing)
      .run();
    console.log(`  ✅ 已清零今天的风险提示累计（${todayBeijing}），重新开始计数`);
    
    // 4. ⚠️ round_stats 永久保留，不删除（用于历史回看）
    console.log('  ℹ️  round_stats 表永久保留，每轮统计实时计算非累计值');
    
    // 4. ⚠️ coin_round_details 永久保留，不删除（用于历史回看）
    console.log('  ℹ️  coin_round_details 表永久保留，可回看任意历史时刻');
    
    // 5. trading_signals 和 alert_signals 永久保留，查询时按日期过滤
    console.log('  ℹ️  trading_signals 和 alert_signals 表永久保留');
    
    console.log('✅ 每日数据清零完成！计数器已清零，所有历史数据完整保留（北京时间）');
  }

  // 增加极端行情累计次数（涨幅≥4%）
  async incrementExtremeUpCount(symbol: string) {
    await this.db
      .prepare(`
        UPDATE price_extremes 
        SET extreme_up_count = extreme_up_count + 1, last_updated = datetime('now')
        WHERE symbol = ?
      `)
      .bind(symbol)
      .run();
  }

  // 增加极端行情累计次数（跌幅≤-3%）
  async incrementExtremeDownCount(symbol: string) {
    await this.db
      .prepare(`
        UPDATE price_extremes 
        SET extreme_down_count = extreme_down_count + 1, last_updated = datetime('now')
        WHERE symbol = ?
      `)
      .bind(symbol)
      .run();
  }

  // 重置极端上涨计次
  async resetExtremeUpCount(symbol: string) {
    await this.db
      .prepare(`
        UPDATE price_extremes 
        SET extreme_up_count = 0, last_updated = datetime('now')
        WHERE symbol = ?
      `)
      .bind(symbol)
      .run();
  }

  // 重置极端下跌计次
  async resetExtremeDownCount(symbol: string) {
    await this.db
      .prepare(`
        UPDATE price_extremes 
        SET extreme_down_count = 0, last_updated = datetime('now')
        WHERE symbol = ?
      `)
      .bind(symbol)
      .run();
  }

  // 保存轮次统计
  async saveRoundStat(roundTime: string, stats: any) {
    await this.db
      .prepare(`
        INSERT INTO round_stats (
          round_time, green_count, red_count, green_ratio,
          extreme_up_count, extreme_down_count, surge_count, crash_count, risk_alert_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
      `)
      .bind(
        roundTime,
        stats.green_count,
        stats.red_count,
        stats.green_ratio,
        stats.extreme_up_count,
        stats.extreme_down_count,
        stats.surge_count,
        stats.crash_count,
        stats.risk_alert_count
      )
      .run();
  }

  // 保存单币轮次详情
  async saveCoinRoundDetail(symbol: string, roundTime: string, detail: any) {
    await this.db
      .prepare(`
        INSERT INTO coin_round_details (
          symbol, round_time, price, prev_price, change_amount, change_percent,
          is_green, is_extreme_up, is_extreme_down, is_surge, is_crash, rank_in_round, change_24h,
          previous_round_time, change_vs_prev_round, is_surge_vs_prev, is_crash_vs_prev
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `)
      .bind(
        symbol,
        roundTime,
        detail.price,
        detail.prev_price,
        detail.change_amount,
        detail.change_percent,
        detail.is_green ? 1 : 0,
        detail.is_extreme_up ? 1 : 0,
        detail.is_extreme_down ? 1 : 0,
        detail.is_surge ? 1 : 0,
        detail.is_crash ? 1 : 0,
        detail.rank_in_round,
        detail.change_24h || 0,
        detail.previous_round_time || null,
        detail.change_vs_prev_round || 0,
        detail.is_surge_vs_prev || 0,
        detail.is_crash_vs_prev || 0
      )
      .run();
  }

  // 更新或创建日统计（支持部分字段更新）
  async updateDailyStat(date: string, symbol: string, updates: any) {
    const existing = await this.db
      .prepare('SELECT * FROM daily_stats WHERE date = ? AND symbol = ?')
      .bind(date, symbol)
      .first();

    if (existing) {
      // 只更新提供的字段，保留其他字段的原值
      const updatedData = {
        total_surges: updates.total_surges !== undefined ? updates.total_surges : (existing as any).total_surges,
        total_crashes: updates.total_crashes !== undefined ? updates.total_crashes : (existing as any).total_crashes,
        new_high_count: updates.new_high_count !== undefined ? updates.new_high_count : (existing as any).new_high_count,
        new_low_count: updates.new_low_count !== undefined ? updates.new_low_count : (existing as any).new_low_count,
        market_trend: updates.market_trend !== undefined ? updates.market_trend : (existing as any).market_trend,
        trend_strength: updates.trend_strength !== undefined ? updates.trend_strength : (existing as any).trend_strength,
        star_rating: updates.star_rating !== undefined ? updates.star_rating : (existing as any).star_rating,
        star_type: updates.star_type !== undefined ? updates.star_type : (existing as any).star_type
      };

      await this.db
        .prepare(`
          UPDATE daily_stats 
          SET total_surges = ?, total_crashes = ?, new_high_count = ?, new_low_count = ?,
              market_trend = ?, trend_strength = ?, star_rating = ?, star_type = ?
          WHERE date = ? AND symbol = ?
        `)
        .bind(
          updatedData.total_surges,
          updatedData.total_crashes,
          updatedData.new_high_count,
          updatedData.new_low_count,
          updatedData.market_trend,
          updatedData.trend_strength,
          updatedData.star_rating,
          updatedData.star_type,
          date,
          symbol
        )
        .run();
    } else {
      // 创建新记录，未提供的字段使用默认值
      await this.db
        .prepare(`
          INSERT INTO daily_stats (
            date, symbol, total_surges, total_crashes, new_high_count, new_low_count,
            market_trend, trend_strength, star_rating, star_type
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `)
        .bind(
          date,
          symbol,
          updates.total_surges || 0,
          updates.total_crashes || 0,
          updates.new_high_count || 0,
          updates.new_low_count || 0,
          updates.market_trend || 'neutral',
          updates.trend_strength || 0,
          updates.star_rating || 0,
          updates.star_type || 'none'
        )
        .run();
    }
  }

  // 获取今日统计
  async getTodayStats(date: string) {
    const result = await this.db
      .prepare('SELECT * FROM daily_stats WHERE date = ?')
      .bind(date)
      .all();
    return result.results;
  }

  // 🆕 获取今天的风险提示累计次数
  async getTodayRiskAlertCount(date: string): Promise<number> {
    const result = await this.db
      .prepare(`
        SELECT risk_alert_cumulative 
        FROM daily_risk_alerts 
        WHERE date = ?
      `)
      .bind(date)
      .first();
    return (result as any)?.risk_alert_cumulative || 0;
  }

  // 🆕 保存今天的风险提示累计次数（带最后事件时间）
  async saveTodayRiskAlertCount(date: string, count: number, lastEventTime?: string) {
    if (lastEventTime) {
      await this.db
        .prepare(`
          INSERT INTO daily_risk_alerts (date, risk_alert_cumulative, last_event_time)
          VALUES (?, ?, ?)
          ON CONFLICT(date) DO UPDATE SET
            risk_alert_cumulative = excluded.risk_alert_cumulative,
            last_event_time = excluded.last_event_time
        `)
        .bind(date, count, lastEventTime)
        .run();
    } else {
      await this.db
        .prepare(`
          INSERT INTO daily_risk_alerts (date, risk_alert_cumulative)
          VALUES (?, ?)
          ON CONFLICT(date) DO UPDATE SET
            risk_alert_cumulative = excluded.risk_alert_cumulative
        `)
        .bind(date, count)
        .run();
    }
  }

  // 🆕 获取今天最后一次风险事件时间
  async getLastRiskEventTime(date: string): Promise<string | null> {
    const result = await this.db
      .prepare(`
        SELECT last_event_time 
        FROM daily_risk_alerts 
        WHERE date = ?
      `)
      .bind(date)
      .first();
    return (result as any)?.last_event_time || null;
  }

  // 🆕 保存风险事件详情
  async saveRiskAlertEvent(roundTime: string, greenRatio: number, totalCoins: number) {
    const eventTime = new Date().toISOString();
    await this.db
      .prepare(`
        INSERT INTO risk_alert_events (event_time, round_time, green_ratio, total_coins)
        VALUES (?, ?, ?, ?)
      `)
      .bind(eventTime, roundTime, greenRatio, totalCoins)
      .run();
    return eventTime;
  }

  // 🆕 获取所有风险事件记录
  async getAllRiskAlertEvents(limit: number = 100) {
    const result = await this.db
      .prepare(`
        SELECT * FROM risk_alert_events 
        ORDER BY event_time DESC 
        LIMIT ?
      `)
      .bind(limit)
      .all();
    return result.results;
  }

  // 🆕 获取今日风险事件记录
  async getTodayRiskAlertEvents(date: string) {
    // 转换为UTC时间范围
    const bjDate = new Date(`${date}T00:00:00+08:00`);
    const startUTC = bjDate.toISOString();
    const endDate = new Date(bjDate.getTime() + 24 * 60 * 60 * 1000);
    const endUTC = endDate.toISOString();

    const result = await this.db
      .prepare(`
        SELECT * FROM risk_alert_events 
        WHERE event_time >= ? AND event_time < ?
        ORDER BY event_time DESC
      `)
      .bind(startUTC, endUTC)
      .all();
    return result.results;
  }

  // 获取指定日期的所有轮次统计（用于修正）
  async getRoundStatsByDate(date: string) {
    // 北京时间日期转换为UTC时间范围
    // 例如: 2025-10-27 北京时间 -> 2025-10-26T16:00:00.000Z ~ 2025-10-27T15:59:59.999Z UTC
    const bjDate = new Date(`${date}T00:00:00+08:00`);
    const startTime = new Date(bjDate.getTime()).toISOString();
    const endTime = new Date(bjDate.getTime() + 24 * 60 * 60 * 1000 - 1).toISOString();
    
    const result = await this.db
      .prepare(`
        SELECT * FROM round_stats 
        WHERE round_time >= ? AND round_time <= ?
        ORDER BY round_time DESC
      `)
      .bind(startTime, endTime)
      .all();
    return result.results;
  }

  // 更新轮次统计的风险提示次数
  async updateRoundRiskAlert(roundTime: string, riskAlertCount: number) {
    await this.db
      .prepare(`
        UPDATE round_stats 
        SET risk_alert_count = ?
        WHERE round_time = ?
      `)
      .bind(riskAlertCount, roundTime)
      .run();
  }

  // 更新币种优先级
  async updateCoinPriority(symbol: string, level: number, lowRatio: number, highRatio: number) {
    await this.db
      .prepare(`
        INSERT INTO coin_priority (symbol, level, low_ratio, high_ratio)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
          level = excluded.level,
          low_ratio = excluded.low_ratio,
          high_ratio = excluded.high_ratio,
          last_updated = datetime('now')
      `)
      .bind(symbol, level, lowRatio, highRatio)
      .run();
    
    // Track level 2 history for support line rules
    if (level <= 2) {
      await this.trackLevelHistory(symbol, level);
    }
  }

  // Track coin level history for 7-day support line rules
  private async trackLevelHistory(symbol: string, level: number) {
    try {
      // Check if this level record already exists and is active
      const existing = await this.db
        .prepare(`
          SELECT id, reached_at FROM coin_level_history
          WHERE symbol = ? AND level = ? AND is_active = 1
          ORDER BY reached_at DESC
          LIMIT 1
        `)
        .bind(symbol, level)
        .first();

      const now = new Date();
      
      // If record exists and was created within last 7 days, don't create duplicate
      if (existing) {
        const reachedAt = new Date(existing.reached_at as string);
        const daysSince = (now.getTime() - reachedAt.getTime()) / (1000 * 60 * 60 * 24);
        if (daysSince < 7) {
          return; // Don't create duplicate
        }
      }

      // Create new level history record
      const levelId = `level_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const reachedAt = now.toISOString();
      const expiredAt = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000).toISOString(); // 7 days later

      await this.db
        .prepare(`
          INSERT INTO coin_level_history (
            id, symbol, level, reached_at, expired_at, is_active, created_at
          ) VALUES (?, ?, ?, ?, ?, 1, ?)
        `)
        .bind(levelId, symbol, level, reachedAt, expiredAt, now.toISOString())
        .run();

      console.log(`📝 Tracked level ${level} for ${symbol} (expires in 7 days)`);
    } catch (error) {
      console.error(`Failed to track level history for ${symbol}:`, error);
    }
  }

  // 获取最新的轮次统计
  async getLatestRoundStats(limit: number = 10) {
    const result = await this.db
      .prepare('SELECT * FROM round_stats ORDER BY round_time DESC LIMIT ?')
      .bind(limit)
      .all();
    return result.results;
  }

  // 获取最新的币种详情
  async getLatestCoinDetails(roundTime: string) {
    const result = await this.db
      .prepare('SELECT * FROM coin_round_details WHERE round_time = ? ORDER BY rank_in_round')
      .bind(roundTime)
      .all();
    return result.results;
  }

  // 获取所有极值数据
  async getAllPriceExtremes() {
    const result = await this.db
      .prepare('SELECT * FROM price_extremes')
      .all();
    return result.results;
  }

  // 获取最新的极值记录（用于比价页面左栏显示）
  async getLatestExtremeRecords(limit: number = 100) {
    const result = await this.db
      .prepare(`
        SELECT 
          symbol,
          record_type,
          price,
          timestamp
        FROM extreme_records
        ORDER BY timestamp DESC
        LIMIT ?
      `)
      .bind(limit)
      .all();
    return result.results;
  }

  // 获取所有优先级
  async getAllCoinPriorities() {
    const result = await this.db
      .prepare('SELECT * FROM coin_priority ORDER BY level')
      .all();
    return result.results;
  }

  // 获取指定轮次的统计数据
  async getRoundStatByTime(roundTime: string) {
    const result = await this.db
      .prepare('SELECT * FROM round_stats WHERE round_time = ?')
      .bind(roundTime)
      .first();
    return result;
  }

  // 🆕 获取今日创新高/新低的总次数
  async getTodayExtremeCount(date: string, recordType: 'high' | 'low'): Promise<number> {
    // 数据库中存储的是 'new_high' 和 'new_low'
    const dbRecordType = recordType === 'high' ? 'new_high' : 'new_low';
    const result = await this.db
      .prepare(`
        SELECT COUNT(*) as count 
        FROM extreme_records 
        WHERE DATE(timestamp) = ? AND record_type = ?
      `)
      .bind(date, dbRecordType)
      .first();
    return (result as any)?.count || 0;
  }

  // 🆕 获取今日每个币种的V1触发次数（买卖点信号中的V1，按signal_time去重）
  async getTodayV1Counts(date: string): Promise<{ [symbol: string]: number }> {
    // trading_signals table doesn't have operation_tip field
    // Return empty counts for now until K-line data is synced with operation tips
    return {};
  }

  // 🆕 获取今天（北京时间）每个币种的起始价格（使用OKX K线数据）
  async getTodayStartPrices(date: string): Promise<{ [symbol: string]: number }> {
    const result = await this.db
      .prepare(`
        WITH RankedKlines AS (
          SELECT 
            symbol,
            open as price,
            open_time,
            ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY open_time ASC) as rn
          FROM kline_data
          WHERE timeframe = '5m'
          AND date(datetime(open_time/1000, 'unixepoch'), '+8 hours') = ?
        )
        SELECT symbol, price
        FROM RankedKlines
        WHERE rn = 1
      `)
      .bind(date)
      .all();
    
    const prices: { [symbol: string]: number } = {};
    for (const row of result.results as any[]) {
      prices[row.symbol] = row.price;
    }
    return prices;
  }

  // 🆕 获取每个币种最新的K线收盘价（使用OKX K线数据）
  async getLatestKlinePrices(timeframe: string = '5m'): Promise<{ [symbol: string]: number }> {
    const result = await this.db
      .prepare(`
        WITH RankedKlines AS (
          SELECT 
            symbol,
            close as price,
            open_time,
            ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY open_time DESC) as rn
          FROM kline_data
          WHERE timeframe = ?
        )
        SELECT symbol, price
        FROM RankedKlines
        WHERE rn = 1
      `)
      .bind(timeframe)
      .all();
    
    const prices: { [symbol: string]: number } = {};
    for (const row of result.results as any[]) {
      prices[row.symbol] = row.price;
    }
    return prices;
  }

  // 🆕 获取每个币种的OKX永续合约1天K线涨跌幅（作为当天涨幅）
  async getOKXDailyChanges(): Promise<{ [symbol: string]: number }> {
    const coins = await this.getAllCoins();
    const changes: { [symbol: string]: number } = {};
    
    // 🔥 优化：批量请求所有币种（OKX支持单次查询多个交易对）
    // 但为了稳定性，我们分批处理，每批5个币种
    const batchSize = 5;
    for (let i = 0; i < (coins as any[]).length; i += batchSize) {
      const batch = (coins as any[]).slice(i, i + batchSize);
      
      await Promise.all(
        batch.map(async (coin: any) => {
          try {
            const symbol = coin.symbol;
            const instId = `${symbol}-USDT-SWAP`; // OKX永续合约格式
            
            // 查询1天K线，limit=1获取最新的一根
            const url = `https://www.okx.com/api/v5/market/candles?instId=${instId}&bar=1D&limit=1`;
            const response = await fetch(url, {
              signal: AbortSignal.timeout(3000) // 3秒超时
            });
            
            if (response.ok) {
              const result = await response.json();
              
              // OKX返回格式：{code: "0", msg: "", data: [[ts, o, h, l, c, vol, ...]]}
              if (result.code === "0" && result.data && result.data.length > 0) {
                const kline = result.data[0];
                const open = parseFloat(kline[1]);   // 开盘价
                const close = parseFloat(kline[4]);  // 收盘价
                
                if (open > 0) {
                  // 计算涨跌幅 = (收盘价 - 开盘价) / 开盘价 * 100%
                  const changePercent = ((close - open) / open) * 100;
                  changes[symbol] = changePercent;
                }
              }
            }
          } catch (error: any) {
            console.error(`获取 ${coin.symbol} 1天K线涨跌幅失败:`, error.message);
            // 失败时不设置值，使用null
          }
        })
      );
      
      // 批次之间等待100ms，避免请求过快
      if (i + batchSize < (coins as any[]).length) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    }
    
    return changes;
  }

  // 🆕 获取时间段统计（今天、三日、七天的极值触发次数）
  async getTimeRangeStats() {
    // 获取所有币种列表
    const coins = await this.getAllCoins();
    
    // 计算时间边界（使用北京时间 UTC+8）
    const now = new Date();
    const beijingOffset = 8 * 60 * 60 * 1000; // 8小时的毫秒数
    const beijingNow = new Date(now.getTime() + beijingOffset);
    
    // 北京时间今天0点
    const beijingTodayStart = new Date(
      beijingNow.getFullYear(),
      beijingNow.getMonth(),
      beijingNow.getDate()
    );
    // 🔧 修正：从北京时间 1:00 开始算今天（避免刚过0点的历史记录）
    const beijingTodayStartAdjusted = new Date(beijingTodayStart.getTime() + 60 * 60 * 1000); // +1小时
    const todayStart = new Date(beijingTodayStartAdjusted.getTime() - beijingOffset);
    
    const threeDaysAgo = new Date(todayStart.getTime() - 3 * 24 * 60 * 60 * 1000);
    const sevenDaysAgo = new Date(todayStart.getTime() - 7 * 24 * 60 * 60 * 1000);
    
    const todayStartStr = todayStart.toISOString();
    const threeDaysAgoStr = threeDaysAgo.toISOString();
    const sevenDaysAgoStr = sevenDaysAgo.toISOString();
    
    // 获取所有币种的统计数据
    const stats = await Promise.all(
      (coins as any[]).map(async (coin: any) => {
        // 今天的极值记录数
        const todayResult = await this.db
          .prepare(`
            SELECT COUNT(*) as count
            FROM extreme_records
            WHERE symbol = ? AND timestamp >= ?
          `)
          .bind(coin.symbol, todayStartStr)
          .first();
        
        // 三天内的极值记录数
        const threeDayResult = await this.db
          .prepare(`
            SELECT COUNT(*) as count
            FROM extreme_records
            WHERE symbol = ? AND timestamp >= ?
          `)
          .bind(coin.symbol, threeDaysAgoStr)
          .first();
        
        // 七天内的极值记录数
        const sevenDayResult = await this.db
          .prepare(`
            SELECT COUNT(*) as count
            FROM extreme_records
            WHERE symbol = ? AND timestamp >= ?
          `)
          .bind(coin.symbol, sevenDaysAgoStr)
          .first();
        
        return {
          symbol: coin.symbol,
          today: (todayResult as any)?.count || 0,
          three_days: (threeDayResult as any)?.count || 0,
          seven_days: (sevenDayResult as any)?.count || 0
        };
      })
    );
    
    return stats;
  }
}

// 将 CoinGecko ID 转换为符号
export function coingeckoIdToSymbol(id: string): string | null {
  const entry = Object.entries(SYMBOL_TO_COINGECKO_ID).find(([_, value]) => value === id);
  return entry ? entry[0] : null;
}

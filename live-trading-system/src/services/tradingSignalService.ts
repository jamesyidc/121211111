/**
 * 交易信号服务 - 三流合一系统
 * 负责从K线系统提取operation_tip并存储到trading_signals表
 */

import { D1Database } from '@cloudflare/workers-types';

export interface TradingSignal {
  signal_id: string;              // SYMBOL_TIMESTAMP_TYPE
  symbol: string;
  signal_type: string;            // 抄底做多/顶部做空/超跌反弹/通用卖点/高抛/注意启动
  direction: 'LONG' | 'SHORT';    // 交易方向
  signal_category: 'BUY_POINT' | 'SELL_POINT';  // 信号分类
  kline_time: number;             // K线时间戳（毫秒）
  kline_close: number;            // 收盘价
  kline_open?: number;
  kline_high?: number;
  kline_low?: number;
  kline_volume?: number;
  // 技术指标
  rsi_5min?: number;
  rsi_1hour?: number;
  sar?: number;
  sar_change?: number;
  boll_mb?: number;
  boll_ub?: number;
  boll_lb?: number;
  boll_width_change?: number;
  // 市场数据
  homepage_rank?: number;
  change_today?: number;
  bar_10_compare?: number;
  high_48h?: number;
  low_48h?: number;
  drop_from_48h_high?: number;
  rise_from_48h_low?: number;
  volume_change?: number;
  drop_percentage?: number;
  coin_level?: string;
  created_at?: string;
}

export interface KLineData {
  symbol: string;
  time: number;
  close: number;
  open: number;
  high: number;
  low: number;
  volume: number;
  operation_tip?: string;
  // 技术指标
  rsi_5min?: number;
  rsi_1hour?: number;
  sar?: number;
  sar_change?: number;
  boll_mb?: number;
  boll_ub?: number;
  boll_lb?: number;
  boll_width_change?: number;
  // 市场数据
  homepage_rank?: number;
  change_today?: number;
  bar_10_compare?: number;
  high_48h?: number;
  low_48h?: number;
  drop_from_48h_high?: number;
  rise_from_48h_low?: number;
  volume_change?: number;
  drop_percentage?: number;
  level?: string;
}

export class TradingSignalService {
  constructor(private db: D1Database) {}

  /**
   * 从K线数据中提取信号并存储
   * 30秒轮询调用此方法
   */
  async extractAndStoreSignals(klineData: KLineData[]): Promise<{ 
    success: boolean; 
    newSignals: number; 
    duplicates: number; 
  }> {
    let newSignals = 0;
    let duplicates = 0;

    for (const kline of klineData) {
      if (!kline.operation_tip || kline.operation_tip === '') {
        continue;
      }

      try {
        console.log(`🔍 处理信号: ${kline.symbol} - ${kline.operation_tip} @ ${kline.time}`);
        const signal = this.convertKLineToSignal(kline);
        console.log(`📝 转换后信号: ${signal.signal_id}, 方向=${signal.direction}, 类别=${signal.signal_category}`);
        const inserted = await this.insertSignal(signal);
        
        if (inserted) {
          newSignals++;
          console.log(`✅ 信号已插入`);
        } else {
          duplicates++;
          console.log(`⚠️ 信号重复，跳过`);
        }
      } catch (error) {
        console.error(`❌ 提取信号失败 [${kline.symbol}]:`, error);
      }
    }

    return { success: true, newSignals, duplicates };
  }

  /**
   * 将K线数据转换为交易信号
   */
  private convertKLineToSignal(kline: KLineData): TradingSignal {
    const signalType = kline.operation_tip!;
    const { direction, category } = this.classifySignal(signalType);
    
    // 生成唯一信号ID: SYMBOL_TIMESTAMP_TYPE
    const signalId = `${kline.symbol}_${kline.time}_${signalType.replace(/\s+/g, '_')}`;

    return {
      signal_id: signalId,
      symbol: kline.symbol,
      signal_type: signalType,
      direction,
      signal_category: category,
      kline_time: kline.time,
      kline_close: kline.close,
      kline_open: kline.open,
      kline_high: kline.high,
      kline_low: kline.low,
      kline_volume: kline.volume,
      // 技术指标
      rsi_5min: kline.rsi_5min,
      rsi_1hour: kline.rsi_1hour,
      sar: kline.sar,
      sar_change: kline.sar_change,
      boll_mb: kline.boll_mb,
      boll_ub: kline.boll_ub,
      boll_lb: kline.boll_lb,
      boll_width_change: kline.boll_width_change,
      // 市场数据
      homepage_rank: kline.homepage_rank,
      change_today: kline.change_today,
      bar_10_compare: kline.bar_10_compare,
      high_48h: kline.high_48h,
      low_48h: kline.low_48h,
      drop_from_48h_high: kline.drop_from_48h_high,
      rise_from_48h_low: kline.rise_from_48h_low,
      volume_change: kline.volume_change,
      drop_percentage: kline.drop_percentage,
      coin_level: kline.level,
    };
  }

  /**
   * 根据信号类型分类方向和类别
   */
  private classifySignal(signalType: string): { 
    direction: 'LONG' | 'SHORT'; 
    category: 'BUY_POINT' | 'SELL_POINT';
  } {
    // 买点信号（做多开仓）
    const longBuySignals = ['抄底做多', '超跌反弹', '注意启动'];
    // 卖点信号（做多平仓）- 包括各种顶部/回调/诱多信号
    const longSellSignals = ['通用卖点', '高抛', '急杀诱多', '顶部诱多', '回调诱多'];
    // 买点信号（做空开仓）
    const shortBuySignals = ['顶部做空', '高位做空'];
    // 卖点信号（做空平仓）- 包括底部/反弹/诱空信号
    const shortSellSignals = ['底部平空', '空头陷阱', '底部诱空'];

    if (longBuySignals.includes(signalType)) {
      return { direction: 'LONG', category: 'BUY_POINT' };
    } else if (longSellSignals.includes(signalType)) {
      return { direction: 'LONG', category: 'SELL_POINT' };
    } else if (shortBuySignals.includes(signalType)) {
      return { direction: 'SHORT', category: 'BUY_POINT' };
    } else if (shortSellSignals.includes(signalType)) {
      return { direction: 'SHORT', category: 'SELL_POINT' };
    }

    // 未知信号类型，记录警告并默认为做多买点
    console.warn(`⚠️ 未知信号类型: ${signalType}, 默认分类为 LONG BUY_POINT`);
    return { direction: 'LONG', category: 'BUY_POINT' };
  }

  /**
   * 插入信号到数据库（带去重）
   */
  private async insertSignal(signal: TradingSignal): Promise<boolean> {
    try {
      // 确保NOT NULL字段有默认值
      const open = signal.kline_open ?? signal.kline_close;
      const high = signal.kline_high ?? signal.kline_close;
      const low = signal.kline_low ?? signal.kline_close;
      const volume = signal.kline_volume ?? 0;
      
      const result = await this.db
        .prepare(`
          INSERT INTO trading_signals (
            signal_id, symbol, signal_type, direction, signal_category,
            kline_time, kline_close, kline_open, kline_high, kline_low, kline_volume,
            rsi_5min, rsi_1hour, sar, sar_change,
            boll_mb, boll_ub, boll_lb, boll_width_change,
            homepage_rank, change_today, bar_10_compare,
            high_48h, low_48h, drop_from_48h_high, rise_from_48h_low
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `)
        .bind(
          signal.signal_id,
          signal.symbol,
          signal.signal_type,
          signal.direction,
          signal.signal_category,
          signal.kline_time,
          signal.kline_close,
          open,
          high,
          low,
          volume,
          // 技术指标
          signal.rsi_5min ?? null,
          signal.rsi_1hour ?? null,
          signal.sar ?? null,
          signal.sar_change ?? null,
          signal.boll_mb ?? null,
          signal.boll_ub ?? null,
          signal.boll_lb ?? null,
          signal.boll_width_change ?? null,
          // 市场数据
          signal.homepage_rank ?? null,
          signal.change_today ?? null,
          signal.bar_10_compare ?? null,
          signal.high_48h ?? null,
          signal.low_48h ?? null,
          signal.drop_from_48h_high ?? null,
          signal.rise_from_48h_low ?? null
        )
        .run();

      return result.success;
    } catch (error: any) {
      // UNIQUE constraint violation - 信号已存在
      if (error.message?.includes('UNIQUE constraint')) {
        console.log(`⚠️ 信号已存在（UNIQUE约束）`);
        return false;
      }
      console.error(`❌ 插入信号出错:`, error);
      throw error;
    }
  }

  /**
   * 获取最近的信号
   */
  async getRecentSignals(limit: number = 50): Promise<TradingSignal[]> {
    const result = await this.db
      .prepare(`
        SELECT * FROM trading_signals 
        ORDER BY created_at DESC 
        LIMIT ?
      `)
      .bind(limit)
      .all();

    return result.results as TradingSignal[];
  }

  /**
   * 获取特定币种的最新信号
   */
  async getLatestSignalForSymbol(
    symbol: string, 
    signalCategory: 'BUY_POINT' | 'SELL_POINT'
  ): Promise<TradingSignal | null> {
    const result = await this.db
      .prepare(`
        SELECT * FROM trading_signals 
        WHERE symbol = ? AND signal_category = ?
        ORDER BY kline_time DESC 
        LIMIT 1
      `)
      .bind(symbol, signalCategory)
      .all();

    return result.results.length > 0 ? (result.results[0] as TradingSignal) : null;
  }

  /**
   * 按信号类型统计
   */
  async getSignalStatistics(): Promise<any[]> {
    const result = await this.db
      .prepare(`
        SELECT 
          signal_type,
          direction,
          signal_category,
          COUNT(*) as count,
          MIN(kline_time) as first_seen,
          MAX(kline_time) as last_seen
        FROM trading_signals
        GROUP BY signal_type, direction, signal_category
        ORDER BY count DESC
      `)
      .all();

    return result.results;
  }
}

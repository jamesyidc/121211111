// 连续上涨占优统计服务
// 
// 核心定义：
// - 占比下跌 = 往前40根K线中，(下降通道 + 下跌衰竭) 的K线占比
// - 占比上涨 = 往前40根K线中，(上升通道 + 上升衰竭) 的K线占比
// - 上涨占优 = up_channel_exhaustion_ratio > down_channel_exhaustion_ratio
//
// 数据来源：从 klineService.getKlineWithIndicators() 获取带技术指标的K线数据
// 重要：必须使用已计算好的 up/down_channel_exhaustion_ratio 字段

import { KlineService } from './klineService';

export class ConsecutiveRiseService {
  private db: D1Database;

  constructor(db: D1Database) {
    this.db = db;
  }

  /**
   * 分析今天的K线数据，重新计算连续统计（每天0点清零）
   * 使用 klineService 获取带技术指标的K线数据
   * 注意：仅统计今天（当天0点到现在）的K线，不包括历史数据
   */
  async analyzeHistoricalData(timeframe: string = '5m', limit: number = 300) {
    try {
      console.log(`开始分析今天的K线数据 (timeframe: ${timeframe}, limit: ${limit})...`);

      // 清空现有统计数据
      await this.db
        .prepare('DELETE FROM consecutive_rise_dominance')
        .run();

      // 获取所有币种列表
      const symbolsResult = await this.db
        .prepare('SELECT DISTINCT symbol FROM kline_data WHERE timeframe = ? ORDER BY symbol')
        .bind(timeframe)
        .all();

      const symbols = symbolsResult.results.map(r => r.symbol as string);
      console.log(`找到 ${symbols.length} 个币种`);

      let processedCount = 0;

      // 逐个币种分析
      for (const symbol of symbols) {
        try {
          await this.analyzeSymbolKlines(symbol, timeframe, limit);
          processedCount++;
          
          if (processedCount % 5 === 0) {
            console.log(`已处理 ${processedCount}/${symbols.length} 个币种...`);
          }
        } catch (error: any) {
          console.error(`处理 ${symbol} 失败:`, error.message);
        }
      }

      console.log(`今天数据分析完成，共处理 ${processedCount} 个币种`);

      return {
        success: true,
        processedSymbols: processedCount,
        totalSymbols: symbols.length,
        timeframe,
        message: '历史数据分析完成'
      };
    } catch (error: any) {
      console.error('分析历史数据失败:', error);
      throw error;
    }
  }

  /**
   * 分析单个币种今天的K线数据（每天0点清零，仅统计当天）
   * 使用 klineService 获取带占比字段的K线数据
   */
  private async analyzeSymbolKlines(symbol: string, timeframe: string, limit: number) {
    // 使用 klineService 获取带技术指标的K线数据
    const klineService = new KlineService(this.db);
    const result = await klineService.getKlineWithIndicators(symbol, timeframe, limit);

    if (!result || !result.data || result.data.length === 0) {
      return; // 没有K线数据，跳过
    }

    // 获取今天0点的时间戳（UTC+8时区）
    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    todayStart.setHours(todayStart.getHours() - 8); // 调整为UTC时间
    const todayStartTime = todayStart.toISOString();

    // getKlineWithIndicators返回的数据已经是从新到旧排列
    // 需要反转为从旧到新，以便按时间顺序分析
    let klines = result.data.reverse();

    // 过滤出今天的K线（time格式：2025/10/28 21:55:00）
    klines = klines.filter(k => {
      // 将时间格式转换为可比较的格式
      const klineDate = new Date(k.time.replace(/\//g, '-').replace(' ', 'T') + 'Z');
      return klineDate >= todayStart;
    });

    if (klines.length === 0) {
      // 今天没有K线数据
      return;
    }

    // 统计今天的连续上涨占优
    let currentStreak = 0;
    let maxStreak = 0;
    let maxStreakStartTime: string | null = null;
    let maxStreakEndTime: string | null = null;
    let lastUpRatio = 0;
    let lastDownRatio = 0;

    for (const kline of klines) {
      const upRatio = kline.up_channel_exhaustion_ratio || 0;
      const downRatio = kline.down_channel_exhaustion_ratio || 0;
      const openTime = kline.time; // 格式：2025/10/28 21:55:00

      lastUpRatio = upRatio;
      lastDownRatio = downRatio;

      // 判断是否上涨占优：占比上涨 > 占比下跌
      const isRiseDominant = upRatio > downRatio;

      if (isRiseDominant) {
        if (currentStreak === 0) {
          // 新的连续开始
          currentStreak = 1;
        } else {
          currentStreak++;
        }

        // 更新今天的最大连续记录
        if (currentStreak > maxStreak) {
          maxStreak = currentStreak;
          maxStreakEndTime = openTime;
          
          // 计算开始时间（往前推N根K线）
          const currentIndex = klines.findIndex(k => k.time === openTime);
          const startIndex = currentIndex - currentStreak + 1;
          if (startIndex >= 0) {
            maxStreakStartTime = klines[startIndex].time;
          } else {
            maxStreakStartTime = openTime;
          }
        }
      } else {
        // 连续中断
        currentStreak = 0;
      }
    }

    // 保存到数据库
    await this.db
      .prepare(`
        INSERT INTO consecutive_rise_dominance (
          symbol, current_streak, max_streak, 
          max_streak_start_time, max_streak_end_time,
          last_check_time, last_high_ratio, last_low_ratio
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `)
      .bind(
        symbol,
        currentStreak,
        maxStreak,
        maxStreakStartTime,
        maxStreakEndTime,
        new Date().toISOString(),
        lastUpRatio,   // 存储占比上涨
        lastDownRatio  // 存储占比下跌
      )
      .run();
  }

  /**
   * 每次K线数据更新后调用，增量更新单个币种的统计
   */
  async updateSymbolKline(symbol: string, timeframe: string = '5m') {
    try {
      // 使用 klineService 获取最新的K线数据（带技术指标）
      const klineService = new KlineService(this.db);
      const result = await klineService.getKlineWithIndicators(symbol, timeframe, 1);

      if (!result || !result.data || result.data.length === 0) {
        return; // 没有K线数据
      }

      const latestKline = result.data[0];
      const upRatio = latestKline.up_channel_exhaustion_ratio || 0;
      const downRatio = latestKline.down_channel_exhaustion_ratio || 0;
      const openTime = latestKline.time;

      // 判断是否上涨占优：占比上涨 > 占比下跌
      const isRiseDominant = upRatio > downRatio;

      // 获取现有统计
      const existing = await this.db
        .prepare('SELECT * FROM consecutive_rise_dominance WHERE symbol = ?')
        .bind(symbol)
        .first();

      if (!existing) {
        // 新币种，创建记录
        await this.db
          .prepare(`
            INSERT INTO consecutive_rise_dominance (
              symbol, current_streak, max_streak,
              max_streak_start_time, max_streak_end_time,
              last_check_time, last_high_ratio, last_low_ratio
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
          `)
          .bind(
            symbol,
            isRiseDominant ? 1 : 0,
            isRiseDominant ? 1 : 0,
            isRiseDominant ? openTime : null,
            isRiseDominant ? openTime : null,
            openTime,
            upRatio,
            downRatio
          )
          .run();
      } else {
        // 更新现有记录
        const currentStreak = existing.current_streak as number;
        const maxStreak = existing.max_streak as number;

        let newCurrentStreak: number;
        let newMaxStreak = maxStreak;
        let newMaxStreakStart = existing.max_streak_start_time as string | null;
        let newMaxStreakEnd = existing.max_streak_end_time as string | null;

        if (isRiseDominant) {
          newCurrentStreak = currentStreak + 1;
          
          if (newCurrentStreak > maxStreak) {
            newMaxStreak = newCurrentStreak;
            newMaxStreakEnd = openTime;
            if (currentStreak === 0) {
              newMaxStreakStart = openTime;
            }
          }
        } else {
          newCurrentStreak = 0;
        }

        await this.db
          .prepare(`
            UPDATE consecutive_rise_dominance
            SET 
              current_streak = ?,
              max_streak = ?,
              max_streak_start_time = ?,
              max_streak_end_time = ?,
              last_check_time = ?,
              last_high_ratio = ?,
              last_low_ratio = ?,
              updated_at = CURRENT_TIMESTAMP
            WHERE symbol = ?
          `)
          .bind(
            newCurrentStreak,
            newMaxStreak,
            newMaxStreakStart,
            newMaxStreakEnd,
            openTime,
            upRatio,
            downRatio,
            symbol
          )
          .run();
      }
    } catch (error: any) {
      console.error(`更新 ${symbol} K线统计失败:`, error);
      throw error;
    }
  }

  /**
   * 获取连续K线数超过指定阈值的币种
   */
  async getCoinsAboveThreshold(threshold: number = 20) {
    try {
      const result = await this.db
        .prepare(`
          SELECT 
            crd.*,
            pe.all_time_high,
            pe.all_time_low
          FROM consecutive_rise_dominance crd
          LEFT JOIN price_extremes pe ON crd.symbol = pe.symbol
          WHERE crd.max_streak >= ?
          ORDER BY crd.max_streak DESC, crd.current_streak DESC
        `)
        .bind(threshold)
        .all();

      return result.results;
    } catch (error: any) {
      console.error('获取连续统计失败:', error);
      throw error;
    }
  }

  /**
   * 获取所有币种的连续统计
   */
  async getAllStats() {
    try {
      const result = await this.db
        .prepare(`
          SELECT 
            crd.*,
            pe.all_time_high,
            pe.all_time_low
          FROM consecutive_rise_dominance crd
          LEFT JOIN price_extremes pe ON crd.symbol = pe.symbol
          ORDER BY crd.max_streak DESC, crd.current_streak DESC
        `)
        .all();

      return result.results;
    } catch (error: any) {
      console.error('获取所有连续统计失败:', error);
      throw error;
    }
  }

  /**
   * 获取统计概览
   */
  async getStatsOverview() {
    try {
      const result = await this.db
        .prepare(`
          SELECT 
            COUNT(*) as total_coins,
            COUNT(CASE WHEN max_streak >= 20 THEN 1 END) as above_20,
            COUNT(CASE WHEN max_streak >= 30 THEN 1 END) as above_30,
            COUNT(CASE WHEN max_streak >= 40 THEN 1 END) as above_40,
            COUNT(CASE WHEN current_streak > 0 THEN 1 END) as currently_rising,
            MAX(max_streak) as max_streak_overall,
            AVG(max_streak) as avg_max_streak
          FROM consecutive_rise_dominance
        `)
        .first();

      return result;
    } catch (error: any) {
      console.error('获取统计概览失败:', error);
      throw error;
    }
  }
}

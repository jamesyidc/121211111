// 震荡收敛统计服务
// 用于记录和统计每次震荡收敛时的布林带宽度数据
import { getBeijingDateString, getBeijingDateDaysAgo } from '../utils/timeUtils';

export interface ConvergenceRecord {
  symbol: string;
  timeframe: string;
  convergence_time: string;
  boll_width: number;
  boll_width_percent: number;
  boll_upper: number;
  boll_middle: number;
  boll_lower: number;
  close_price: number;
  rsi_5min?: number;
  sar_direction?: string;
}

export interface ConvergenceStats {
  symbol: string;
  total_count: number;
  avg_width: number;
  min_width: number;
  max_width: number;
  avg_width_percent: number;
  min_width_percent: number;
  max_width_percent: number;
  recent_records: ConvergenceRecord[];
}

export class ConvergenceStatsService {
  private db: D1Database;

  constructor(db: D1Database) {
    this.db = db;
  }

  // 记录震荡收敛数据
  async recordConvergence(record: ConvergenceRecord): Promise<boolean> {
    try {
      await this.db
        .prepare(`
          INSERT OR IGNORE INTO convergence_stats 
          (symbol, timeframe, convergence_time, boll_width, boll_width_percent, 
           boll_upper, boll_middle, boll_lower, close_price, rsi_5min, sar_direction)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `)
        .bind(
          record.symbol,
          record.timeframe,
          record.convergence_time,
          record.boll_width,
          record.boll_width_percent,
          record.boll_upper,
          record.boll_middle,
          record.boll_lower,
          record.close_price,
          record.rsi_5min || null,
          record.sar_direction || null
        )
        .run();

      return true;
    } catch (error) {
      console.error('记录震荡收敛数据失败:', error);
      return false;
    }
  }

  // 批量记录震荡收敛数据
  async recordMultipleConvergence(records: ConvergenceRecord[]): Promise<number> {
    let successCount = 0;
    
    for (const record of records) {
      const success = await this.recordConvergence(record);
      if (success) successCount++;
    }
    
    return successCount;
  }

  // 获取指定币种的震荡收敛统计（使用北京时间）
  async getConvergenceStats(symbol: string, days: number = 30): Promise<ConvergenceStats | null> {
    try {
      // 🔥 使用北京时间计算N天前的日期
      const cutoffDateStr = getBeijingDateDaysAgo(days);

      // 统计数据（使用 DATE(created_at) 而不是 DATE(convergence_time)，因为时间格式问题）
      const statsResult = await this.db
        .prepare(`
          SELECT 
            symbol,
            COUNT(*) as total_count,
            AVG(boll_width) as avg_width,
            MIN(boll_width) as min_width,
            MAX(boll_width) as max_width,
            AVG(boll_width_percent) as avg_width_percent,
            MIN(boll_width_percent) as min_width_percent,
            MAX(boll_width_percent) as max_width_percent
          FROM convergence_stats
          WHERE symbol = ? AND DATE(created_at) >= ?
          GROUP BY symbol
        `)
        .bind(symbol, cutoffDateStr)
        .first();

      if (!statsResult) {
        return null;
      }

      // 获取最近的记录
      const recentResult = await this.db
        .prepare(`
          SELECT *
          FROM convergence_stats
          WHERE symbol = ? AND DATE(created_at) >= ?
          ORDER BY created_at DESC
          LIMIT 20
        `)
        .bind(symbol, cutoffDateStr)
        .all();

      return {
        symbol: statsResult.symbol as string,
        total_count: statsResult.total_count as number,
        avg_width: statsResult.avg_width as number,
        min_width: statsResult.min_width as number,
        max_width: statsResult.max_width as number,
        avg_width_percent: statsResult.avg_width_percent as number,
        min_width_percent: statsResult.min_width_percent as number,
        max_width_percent: statsResult.max_width_percent as number,
        recent_records: (recentResult.results || []) as ConvergenceRecord[]
      };
    } catch (error) {
      console.error('获取震荡收敛统计失败:', error);
      return null;
    }
  }

  // 获取所有币种的震荡收敛统计（简化版，使用北京时间）
  async getAllConvergenceStats(days: number = 30): Promise<{ [symbol: string]: ConvergenceStats }> {
    try {
      // 🔥 使用北京时间计算N天前的日期
      const cutoffDateStr = getBeijingDateDaysAgo(days);

      const result = await this.db
        .prepare(`
          SELECT 
            symbol,
            COUNT(*) as total_count,
            AVG(boll_width) as avg_width,
            MIN(boll_width) as min_width,
            MAX(boll_width) as max_width,
            AVG(boll_width_percent) as avg_width_percent,
            MIN(boll_width_percent) as min_width_percent,
            MAX(boll_width_percent) as max_width_percent
          FROM convergence_stats
          WHERE DATE(created_at) >= ?
          GROUP BY symbol
          ORDER BY symbol
        `)
        .bind(cutoffDateStr)
        .all();

      const stats: { [symbol: string]: ConvergenceStats } = {};
      
      (result.results || []).forEach((row: any) => {
        stats[row.symbol] = {
          symbol: row.symbol,
          total_count: row.total_count,
          avg_width: row.avg_width,
          min_width: row.min_width,
          max_width: row.max_width,
          avg_width_percent: row.avg_width_percent,
          min_width_percent: row.min_width_percent,
          max_width_percent: row.max_width_percent,
          recent_records: [] // 简化版不包含详细记录
        };
      });

      return stats;
    } catch (error) {
      console.error('获取所有震荡收敛统计失败:', error);
      return {};
    }
  }

  // 获取今日震荡收敛次数（使用北京时间）
  async getTodayConvergenceCount(symbol: string): Promise<number> {
    try {
      // 🔥 使用北京时间的今天日期
      const today = getBeijingDateString();
      
      const result = await this.db
        .prepare(`
          SELECT COUNT(*) as count
          FROM convergence_stats
          WHERE symbol = ? AND DATE(created_at) = ?
        `)
        .bind(symbol, today)
        .first();

      return (result?.count as number) || 0;
    } catch (error) {
      console.error('获取今日震荡收敛次数失败:', error);
      return 0;
    }
  }

  // 清理旧数据（保留最近N天的数据，使用北京时间）
  async cleanOldData(keepDays: number = 90): Promise<number> {
    try {
      // 🔥 使用北京时间计算N天前的日期
      const cutoffDateStr = getBeijingDateDaysAgo(keepDays);

      const result = await this.db
        .prepare(`
          DELETE FROM convergence_stats
          WHERE DATE(created_at) < ?
        `)
        .bind(cutoffDateStr)
        .run();

      console.log(`✅ 清理了 ${result.meta.changes} 条旧的震荡收敛记录`);
      return result.meta.changes || 0;
    } catch (error) {
      console.error('清理旧数据失败:', error);
      return 0;
    }
  }
}

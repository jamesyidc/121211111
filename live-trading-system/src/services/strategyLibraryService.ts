/**
 * 策略库服务 - 三流合一系统
 * 管理交易策略（买点+卖点组合）
 */

import { D1Database } from '@cloudflare/workers-types';

export interface Strategy {
  // ===== 主键和标识 =====
  strategy_id: string;                    // 策略唯一编号 STR_001, STR_002
  strategy_code: string;                  // 策略编号（新表字段）
  strategy_name: string;                  // 策略名称
  
  // ===== 策略类型 =====
  strategy_type: 'LONG' | 'SHORT';        // 做多或做空
  strategy_category?: string;             // 策略分类
  
  // ===== 优先级和状态 =====
  priority: number;                       // 优先级 1-100
  is_enabled: number;                     // 是否启用 0/1
  is_active?: number;                     // 旧字段兼容
  
  // ===== 入场信号配置 =====
  entry_signal_code: string;              // 买点信号编号
  entry_signal_name?: string;             // 买点信号名称
  entry_price_type?: string;              // 买点价格类型: market/limit/optimal
  buy_signal_type?: string;               // 旧字段兼容
  
  // ===== 出场信号配置 - 支持最多5个卖点 =====
  exit_signal_code_1?: string;            // 卖点信号1
  exit_signal_code_2?: string;            // 卖点信号2
  exit_signal_code_3?: string;            // 卖点信号3
  exit_signal_code_4?: string;            // 卖点信号4
  exit_signal_code_5?: string;            // 卖点信号5
  exit_signal_name_1?: string;
  exit_signal_name_2?: string;
  exit_signal_name_3?: string;
  exit_signal_name_4?: string;
  exit_signal_name_5?: string;
  exit_price_type?: string;               // 卖点价格类型
  exit_strategy?: string;                 // 出场策略: any/priority/multiple
  sell_signal_types?: string;             // 旧字段兼容（JSON数组）
  
  // ===== 仓位管理 =====
  position_size_usdt: number;             // 每次开仓金额（USDT）
  position_size_type?: string;            // 仓位类型
  max_positions?: number;                 // 最大同时持仓数
  
  // ===== 分批建仓 =====
  batch_enabled?: number;                 // 是否启用分批 0/1
  batch_count?: number;                   // 分批次数 1-5
  batch_interval_pct?: number;            // 分批间隔百分比
  batch_first_amount?: number;            // 第1次加仓金额
  batch_second_amount?: number;           // 第2次加仓金额
  batch_third_amount?: number;            // 第3次加仓金额
  
  // ===== 持仓时间 =====
  max_holding_period?: number;            // 最大持仓周期（K线数量）
  max_holding_period_unit?: string;       // 周期单位: kline/minutes/hours
  
  // ===== 币种级别过滤 =====
  coin_level_filter_enabled?: number;     // 是否启用币种级别过滤 0/1
  allowed_coin_levels?: string;           // 允许的币种等级（JSON数组）
  include_recent_levels?: number;         // 包含过去7天内达到过的级别 0/1
  blocked_symbols?: string;               // 屏蔽的币种列表（JSON）
  
  // ===== 当日涨幅条件 =====
  daily_change_filter_enabled?: number;   // 是否启用当日涨幅过滤 0/1
  daily_change_condition_type?: string;   // 条件类型
  daily_change_min_pct?: number;          // 最小涨幅百分比
  daily_change_max_pct?: number;          // 最大涨幅百分比
  min_daily_change?: number;              // 旧字段兼容
  max_daily_change?: number;              // 旧字段兼容
  
  // ===== 账户涨跌幅触发条件 =====
  account_gain_trigger_enabled?: number;  // 是否启用账户涨跌幅触发 0/1
  account_gain_operator?: 'greater_than' | 'less_than' | 'between'; // 运算符
  account_gain_value_pct?: number;        // 涨跌幅百分比（相对初始余额）
  account_gain_max_pct?: number;          // 范围最大值（用于between）
  
  // ===== 止盈配置 =====
  take_profit_enabled?: number;           // 是否启用止盈 0/1
  take_profit_pct?: number;               // 止盈百分比（0=不止盈）
  take_profit_strategy?: string;          // 止盈策略
  
  // ===== 止损配置 =====
  stop_loss_enabled?: number;             // 是否启用止损 0/1
  stop_loss_pct?: number;                 // 止损百分比（0=不止损）
  stop_loss_type?: string;                // 止损类型
  
  // ===== 移动止损 =====
  trailing_stop_enabled?: number;         // 是否启用移动止损
  trailing_stop_pct?: number;             // 移动止损百分比
  trailing_activation_pct?: number;       // 移动止损激活百分比
  
  // ===== 其他条件 =====
  min_volume_v1?: number;                 // 最小V1量能
  min_volume_ratio?: number;              // 旧字段兼容
  trading_hours?: string;                 // 交易时段限制（JSON）
  
  // ===== 描述信息 =====
  description?: string;                   // 策略描述
  usage_scenario?: string;                // 适用场景
  risk_level?: string;                    // 风险等级
  
  // ===== 元数据 =====
  is_testing?: number;                    // 是否测试模式
  created_at?: string;
  updated_at?: string;
  last_used_at?: string;
}

export class StrategyLibraryService {
  constructor(private db: D1Database) {}

  /**
   * 创建新策略
   */
  async createStrategy(strategy: Omit<Strategy, 'created_at' | 'updated_at'>): Promise<boolean> {
    try {
      // 构建SQL - 只插入提供的字段
      const fields: string[] = [];
      const placeholders: string[] = [];
      const values: any[] = [];

      // 必填字段
      const requiredFields = [
        'strategy_code', 'strategy_name', 'strategy_type',
        'entry_signal_code', 'position_size_usdt'
      ];

      // 映射旧字段到新字段
      const fieldMapping: Record<string, string> = {
        'strategy_id': 'strategy_code',
        'buy_signal_type': 'entry_signal_code',
        'is_active': 'is_enabled'
      };

      // 处理所有可能的字段
      Object.entries(strategy).forEach(([key, value]) => {
        // 跳过旧的时间戳字段
        if (key === 'created_at' || key === 'updated_at') return;
        
        // 映射字段名
        const fieldName = fieldMapping[key] || key;
        
        // 特殊处理：sell_signal_types 拆分为5个独立字段
        if (key === 'sell_signal_types' && typeof value === 'string') {
          try {
            const sellSignals = JSON.parse(value);
            for (let i = 0; i < 5; i++) {
              const signal = sellSignals[i];
              if (signal) {
                fields.push(`exit_signal_code_${i + 1}`);
                placeholders.push('?');
                values.push(signal);
              }
            }
          } catch (e) {
            console.warn('解析sell_signal_types失败:', e);
          }
          return;
        }

        fields.push(fieldName);
        placeholders.push('?');
        values.push(value ?? null);
      });

      const sql = `
        INSERT INTO strategy_library (${fields.join(', ')})
        VALUES (${placeholders.join(', ')})
      `;

      const result = await this.db
        .prepare(sql)
        .bind(...values)
        .run();

      return result.success;
    } catch (error) {
      console.error('❌ 创建策略失败:', error);
      throw error;
    }
  }

  /**
   * 获取所有激活的策略
   */
  async getActiveStrategies(): Promise<Strategy[]> {
    const result = await this.db
      .prepare(`
        SELECT * FROM strategy_library 
        WHERE is_enabled = 1 
        ORDER BY priority DESC, created_at DESC
      `)
      .all();

    return result.results as Strategy[];
  }

  /**
   * 根据买点信号类型查找匹配的策略
   * 支持信号代码（SIG001）和信号名称（急杀诱多）
   */
  async findStrategiesByBuySignal(buySignalType: string): Promise<Strategy[]> {
    const result = await this.db
      .prepare(`
        SELECT * FROM strategy_library 
        WHERE is_enabled = 1 
          AND (entry_signal_code = ? OR entry_signal_name = ?)
        ORDER BY priority DESC
      `)
      .bind(buySignalType, buySignalType)
      .all();

    return result.results as Strategy[];
  }

  /**
   * 获取单个策略
   */
  async getStrategy(strategyId: string): Promise<Strategy | null> {
    const result = await this.db
      .prepare(`SELECT * FROM strategy_library WHERE strategy_code = ? OR strategy_id = ?`)
      .bind(strategyId, strategyId)
      .all();

    return result.results.length > 0 ? (result.results[0] as Strategy) : null;
  }

  /**
   * 更新策略
   */
  async updateStrategy(
    strategyId: string, 
    updates: Partial<Strategy>
  ): Promise<boolean> {
    const fields: string[] = [];
    const values: any[] = [];

    // 字段映射
    const fieldMapping: Record<string, string> = {
      'strategy_id': 'strategy_code',
      'buy_signal_type': 'entry_signal_code',
      'is_active': 'is_enabled'
    };

    Object.entries(updates).forEach(([key, value]) => {
      if (key !== 'strategy_id' && key !== 'strategy_code' && key !== 'created_at') {
        const fieldName = fieldMapping[key] || key;
        fields.push(`${fieldName} = ?`);
        values.push(value);
      }
    });

    if (fields.length === 0) return false;

    values.push(strategyId);

    const result = await this.db
      .prepare(`
        UPDATE strategy_library 
        SET ${fields.join(', ')}, updated_at = CURRENT_TIMESTAMP
        WHERE strategy_code = ? OR strategy_id = ?
      `)
      .bind(...values, strategyId)
      .run();

    return result.success;
  }

  /**
   * 启用/禁用策略
   */
  async toggleStrategy(strategyId: string, isActive: boolean): Promise<boolean> {
    const result = await this.db
      .prepare(`
        UPDATE strategy_library 
        SET is_enabled = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE strategy_code = ? OR strategy_id = ?
      `)
      .bind(isActive ? 1 : 0, strategyId, strategyId)
      .run();

    return result.success;
  }

  /**
   * 删除策略
   */
  async deleteStrategy(strategyId: string): Promise<boolean> {
    // ✅ 使用 id (数字主键) 或 strategy_code (字符串代码) 来删除
    const isNumericId = !isNaN(Number(strategyId));
    const idValue = isNumericId ? Number(strategyId) : strategyId;
    
    // 🔧 先获取 strategy_code，然后清理相关记录
    let strategyCode: string | null = null;
    
    try {
      // 1. 获取策略的 strategy_code（用于清理相关表）
      if (isNumericId) {
        const strategy = await this.db
          .prepare(`SELECT strategy_code FROM strategy_library WHERE id = ?`)
          .bind(idValue)
          .first();
        strategyCode = strategy?.strategy_code || null;
      } else {
        strategyCode = strategyId;
      }
      
      // 2. 如果有 strategy_code，清理 completed_strategy_pool 中的相关记录
      // completed_strategy_pool.strategy_id 实际存储的是 strategy_code 值
      if (strategyCode) {
        await this.db
          .prepare(`DELETE FROM completed_strategy_pool WHERE strategy_id = ?`)
          .bind(strategyCode)
          .run();
      }
      
      // 3. 删除策略本身
      const query = isNumericId 
        ? `DELETE FROM strategy_library WHERE id = ?`
        : `DELETE FROM strategy_library WHERE strategy_code = ?`;
      
      const result = await this.db
        .prepare(query)
        .bind(idValue)
        .run();
      
      return result.success;
    } catch (error) {
      console.error('删除策略失败:', error);
      throw error;
    }
  }

  /**
   * 生成下一个策略ID
   */
  async generateNextStrategyId(): Promise<string> {
    const result = await this.db
      .prepare(`
        SELECT strategy_code FROM strategy_library 
        ORDER BY strategy_code DESC 
        LIMIT 1
      `)
      .all();

    if (result.results.length === 0) {
      return 'STR001';
    }

    const lastId = (result.results[0] as any).strategy_code;
    const match = lastId.match(/STR(\d+)/);
    
    if (match) {
      const nextNum = parseInt(match[1]) + 1;
      return `STR${String(nextNum).padStart(3, '0')}`;
    }

    return 'STR001';
  }

  /**
   * 获取策略统计
   */
  async getStrategyStatistics(): Promise<any> {
    const result = await this.db
      .prepare(`
        SELECT 
          COUNT(*) as total_strategies,
          SUM(CASE WHEN is_enabled = 1 THEN 1 ELSE 0 END) as active_strategies,
          COUNT(DISTINCT entry_signal_code) as unique_buy_signals,
          AVG(position_size_usdt) as avg_position_size
        FROM strategy_library
      `)
      .all();

    return result.results[0];
  }
}

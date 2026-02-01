/**
 * 系统设置服务
 * 管理所有可调参数
 */

export interface Setting {
  id: number;
  setting_key: string;
  setting_value: string;
  setting_type: string;
  display_name: string;
  description: string;
  category: string;
  updated_at: string;
}

export class SettingsService {
  private db: D1Database;

  constructor(db: D1Database) {
    this.db = db;
  }

  /**
   * 获取所有设置
   */
  async getAllSettings(): Promise<Setting[]> {
    const result = await this.db
      .prepare('SELECT * FROM system_settings ORDER BY category, id')
      .all();
    
    return result.results as Setting[];
  }

  /**
   * 按分类获取设置
   */
  async getSettingsByCategory(category: string): Promise<Setting[]> {
    const result = await this.db
      .prepare('SELECT * FROM system_settings WHERE category = ? ORDER BY id')
      .bind(category)
      .all();
    
    return result.results as Setting[];
  }

  /**
   * 获取单个设置值
   */
  async getSetting(key: string): Promise<string | null> {
    const result = await this.db
      .prepare('SELECT setting_value FROM system_settings WHERE setting_key = ?')
      .bind(key)
      .first();
    
    return result?.setting_value || null;
  }

  /**
   * 获取数字类型设置值
   */
  async getNumberSetting(key: string, defaultValue: number = 0): Promise<number> {
    const value = await this.getSetting(key);
    return value ? parseFloat(value) : defaultValue;
  }

  /**
   * 更新设置值
   */
  async updateSetting(key: string, value: string): Promise<void> {
    await this.db
      .prepare(`
        UPDATE system_settings 
        SET setting_value = ?, updated_at = CURRENT_TIMESTAMP
        WHERE setting_key = ?
      `)
      .bind(value, key)
      .run();
  }

  /**
   * 批量更新设置
   */
  async updateSettings(settings: { key: string; value: string }[]): Promise<void> {
    const statements = settings.map(s => 
      this.db
        .prepare(`
          UPDATE system_settings 
          SET setting_value = ?, updated_at = CURRENT_TIMESTAMP
          WHERE setting_key = ?
        `)
        .bind(s.value, s.key)
    );
    
    await this.db.batch(statements);
  }

  /**
   * 获取所有设置的键值对形式
   */
  async getSettingsMap(): Promise<Record<string, string>> {
    const settings = await this.getAllSettings();
    const map: Record<string, string> = {};
    
    settings.forEach(s => {
      map[s.setting_key] = s.setting_value;
    });
    
    return map;
  }

  /**
   * 重置所有设置为默认值
   */
  async resetToDefaults(): Promise<void> {
    // 删除所有设置
    await this.db.prepare('DELETE FROM system_settings').run();
    
    // 重新插入默认值（这会触发迁移中的默认值）
    // 实际上应该重新执行插入语句
    const defaultSettings = [
      { key: 'extreme_up_threshold', value: '4', type: 'number', name: '极端上涨阈值(%)', desc: '单轮涨幅达到此值算极端上涨', category: 'extremes' },
      { key: 'extreme_down_threshold', value: '-3', type: 'number', name: '极端下跌阈值(%)', desc: '单轮跌幅达到此值算极端下跌', category: 'extremes' },
      { key: 'surge_threshold', value: '1', type: 'number', name: '急涨阈值(%)', desc: '相对上一轮涨幅达到此值算急涨', category: 'surge_crash' },
      { key: 'crash_threshold', value: '-1', type: 'number', name: '急跌阈值(%)', desc: '相对上一轮跌幅达到此值算急跌', category: 'surge_crash' },
      { key: 'risk_alert_green_ratio', value: '0', type: 'number', name: '全绿风险比例(%)', desc: '绿色占比达到此值触发风险提示', category: 'risk' },
      { key: 'new_high_reset_threshold', value: '3', type: 'number', name: '创新高重置阈值', desc: '连续N次未创新高则重置计数', category: 'extremes' },
      { key: 'new_low_reset_threshold', value: '3', type: 'number', name: '创新低重置阈值', desc: '连续N次未创新低则重置计数', category: 'extremes' },
      { key: 'rsi_period', value: '14', type: 'number', name: 'RSI周期', desc: 'RSI指标计算周期', category: 'indicators' },
      { key: 'boll_period', value: '20', type: 'number', name: 'BOLL周期', desc: '布林带计算周期', category: 'indicators' },
      { key: 'boll_k', value: '2', type: 'number', name: 'BOLL标准差倍数', desc: '布林带上下轨标准差倍数', category: 'indicators' },
      { key: 'sar_af', value: '0.02', type: 'number', name: 'SAR加速因子', desc: 'SAR指标初始加速因子', category: 'indicators' },
      { key: 'sar_max_af', value: '0.2', type: 'number', name: 'SAR最大加速因子', desc: 'SAR指标最大加速因子', category: 'indicators' },
      { key: 'analysis_interval', value: '300000', type: 'number', name: '分析间隔(毫秒)', desc: '自动价格分析的时间间隔', category: 'general' },
      { key: 'kline_sync_interval', value: '900000', type: 'number', name: 'K线同步间隔(毫秒)', desc: 'K线数据同步的时间间隔', category: 'general' }
    ];
    
    const statements = defaultSettings.map(s => 
      this.db
        .prepare(`
          INSERT INTO system_settings (setting_key, setting_value, setting_type, display_name, description, category)
          VALUES (?, ?, ?, ?, ?, ?)
        `)
        .bind(s.key, s.value, s.type, s.name, s.desc, s.category)
    );
    
    await this.db.batch(statements);
  }
}

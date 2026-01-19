/**
 * 数据库初始化服务
 * 确保所有必要的表和索引都存在
 * 在应用启动时自动执行，避免依赖外部迁移工具
 * 
 * 注意：D1的batch()方法可以一次执行多个语句，提高效率
 */

export class DatabaseInitService {
  constructor(private db: D1Database) {}

  /**
   * 初始化所有表（幂等操作，可以重复执行）
   * 使用 D1 batch API 提高初始化效率
   */
  async initializeDatabase(): Promise<{ success: boolean; message: string }> {
    try {
      console.log('🔄 开始初始化数据库...');
      
      // 准备所有创建表的SQL语句
      const statements = [
        // 1. 核心表
        ...this.getCoinsTableSQL(),
        ...this.getPriceRecordsTableSQL(),
        ...this.getDailyStatsTableSQL(),
        ...this.getRoundStatsTableSQL(),
        ...this.getCoinRoundDetailsTableSQL(),
        ...this.getPriceExtremesTableSQL(),
        ...this.getExtremeRecordsTableSQL(),
        ...this.getCoinPriorityTableSQL(),
        
        // 2. K线相关表
        ...this.getKlineDataTableSQL(),
        ...this.getOkxConfigTableSQL(),
        
        // 3. 交易信号相关表
        ...this.getTradingSignalsTableSQL(),
        ...this.getAlertSignalsTableSQL(),
        
        // 4. 仓位追踪表
        ...this.getPositionsTableSQL(),
        ...this.getPositionAlertsTableSQL(),
        
        // 5. 模拟交易表
        ...this.getSimulatedAccountsTableSQL(),
        ...this.getSimulatedTradesTableSQL(),
        ...this.getAccountSnapshotsTableSQL(),
        
        // 6. 其他功能表
        ...this.getConvergenceStatsTableSQL(),
        ...this.getSystemSettingsTableSQL(),
        ...this.getTradingRulesTableSQL(),
        ...this.getTradingStrategiesTableSQL(),
        ...this.getSupportLinesTableSQL(),
        ...this.getConsecutiveRiseDominanceTableSQL(),
      ];
      
      // 使用 batch 批量执行，提高效率
      await this.db.batch(statements.map(sql => this.db.prepare(sql)));
      
      console.log('✅ 数据库初始化完成');
      return { success: true, message: '数据库初始化成功' };
    } catch (error: any) {
      console.error('❌ 数据库初始化失败:', error);
      return { success: false, message: error.message };
    }
  }

  private getCoinsTableSQL(): string[] {
    return [
      `CREATE TABLE IF NOT EXISTS coins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        enabled INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )`,
      `CREATE INDEX IF NOT EXISTS idx_coins_enabled ON coins(enabled)`
    ];
  }

  private async createPriceRecordsTable() {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS price_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        price REAL NOT NULL,
        change_5min REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      CREATE INDEX IF NOT EXISTS idx_price_records_symbol ON price_records(symbol);
      CREATE INDEX IF NOT EXISTS idx_price_records_timestamp ON price_records(timestamp);
    `);
  }

  private async createDailyStatsTable() {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS daily_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        date TEXT NOT NULL,
        max_price REAL,
        min_price REAL,
        change_24h REAL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, date)
      );
      CREATE INDEX IF NOT EXISTS idx_daily_stats_symbol ON daily_stats(symbol);
      CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(date);
    `);
  }

  private async createRoundStatsTable() {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS round_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        round_time TEXT UNIQUE NOT NULL,
        total_coins INTEGER,
        up_coins INTEGER,
        down_coins INTEGER,
        neutral_coins INTEGER,
        max_increase REAL,
        max_decrease REAL,
        avg_change REAL,
        extreme_up_count INTEGER DEFAULT 0,
        extreme_down_count INTEGER DEFAULT 0
      );
      CREATE INDEX IF NOT EXISTS idx_round_stats_time ON round_stats(round_time);
    `);
  }

  private async createCoinRoundDetailsTable() {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS coin_round_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        round_time TEXT NOT NULL,
        price REAL NOT NULL,
        change_5min REAL,
        UNIQUE(symbol, round_time)
      );
      CREATE INDEX IF NOT EXISTS idx_coin_round_symbol ON coin_round_details(symbol);
      CREATE INDEX IF NOT EXISTS idx_coin_round_time ON coin_round_details(round_time);
      CREATE INDEX IF NOT EXISTS idx_coin_round_combined ON coin_round_details(symbol, round_time);
    `);
  }

  private async createPriceExtremesTable() {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS price_extremes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        new_high_count INTEGER DEFAULT 0,
        new_low_count INTEGER DEFAULT 0,
        ath REAL,
        atl REAL,
        ath_time TEXT,
        atl_time TEXT,
        rounds_since_high INTEGER DEFAULT 0,
        rounds_since_low INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol)
      );
      CREATE INDEX IF NOT EXISTS idx_extremes_symbol ON price_extremes(symbol);
    `);
  }

  private async createExtremeRecordsTable() {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS extreme_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        round_time TEXT NOT NULL,
        extreme_type TEXT NOT NULL,
        change_percent REAL NOT NULL,
        price REAL NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      CREATE INDEX IF NOT EXISTS idx_extreme_symbol ON extreme_records(symbol);
      CREATE INDEX IF NOT EXISTS idx_extreme_time ON extreme_records(round_time);
      CREATE INDEX IF NOT EXISTS idx_extreme_type ON extreme_records(extreme_type);
    `);
  }

  private async createCoinPriorityTable() {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS coin_priority (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL UNIQUE,
        level INTEGER NOT NULL DEFAULT 3,
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      CREATE INDEX IF NOT EXISTS idx_priority_symbol ON coin_priority(symbol);
      CREATE INDEX IF NOT EXISTS idx_priority_level ON coin_priority(level);
    `);
  }

  private async createKlineDataTable() {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS kline_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        timeframe TEXT NOT NULL DEFAULT '5m',
        time TEXT NOT NULL,
        open REAL NOT NULL,
        high REAL NOT NULL,
        low REAL NOT NULL,
        close REAL NOT NULL,
        volume REAL NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, timeframe, time)
      );
      CREATE INDEX IF NOT EXISTS idx_kline_symbol ON kline_data(symbol);
      CREATE INDEX IF NOT EXISTS idx_kline_time ON kline_data(time);
      CREATE INDEX IF NOT EXISTS idx_kline_symbol_time ON kline_data(symbol, timeframe, time);
    `);
  }

  private async createOkxConfigTable() {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS okx_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        config_key TEXT UNIQUE NOT NULL,
        config_value TEXT NOT NULL,
        description TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
    `);
  }

  private async createTradingSignalsTable() {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS trading_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        signal_type TEXT NOT NULL,
        trigger_price REAL NOT NULL,
        trigger_time TEXT NOT NULL,
        rsi_5min REAL,
        boll_position TEXT,
        sar_direction TEXT,
        status TEXT DEFAULT 'active',
        notes TEXT,
        telegram_sent INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      CREATE INDEX IF NOT EXISTS idx_signals_symbol ON trading_signals(symbol);
      CREATE INDEX IF NOT EXISTS idx_signals_type ON trading_signals(signal_type);
      CREATE INDEX IF NOT EXISTS idx_signals_time ON trading_signals(trigger_time);
      CREATE INDEX IF NOT EXISTS idx_signals_status ON trading_signals(status);
    `);
  }

  private async createAlertSignalsTable() {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS alert_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        signal_type TEXT NOT NULL,
        trigger_price REAL NOT NULL,
        trigger_time TEXT NOT NULL,
        rsi_5min REAL,
        boll_position TEXT,
        sar_direction TEXT,
        ma_direction TEXT,
        channel_state TEXT,
        boll_width_change REAL,
        status TEXT DEFAULT 'active',
        notes TEXT,
        telegram_sent INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      CREATE INDEX IF NOT EXISTS idx_alert_signals_symbol ON alert_signals(symbol);
      CREATE INDEX IF NOT EXISTS idx_alert_signals_type ON alert_signals(signal_type);
      CREATE INDEX IF NOT EXISTS idx_alert_signals_time ON alert_signals(trigger_time);
      CREATE INDEX IF NOT EXISTS idx_alert_signals_status ON alert_signals(status);
      CREATE INDEX IF NOT EXISTS idx_alert_signals_telegram ON alert_signals(telegram_sent);
    `);
  }

  private async createPositionsTable() {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        entry_price REAL NOT NULL,
        quantity REAL NOT NULL,
        entry_time TEXT NOT NULL,
        exit_price REAL,
        exit_time TEXT,
        pnl_percent REAL,
        status TEXT DEFAULT 'open',
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
      CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
      CREATE INDEX IF NOT EXISTS idx_positions_entry_time ON positions(entry_time);
    `);
  }

  private async createPositionAlertsTable() {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS position_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        position_id INTEGER NOT NULL,
        alert_type TEXT NOT NULL,
        alert_price REAL NOT NULL,
        alert_time TEXT NOT NULL,
        message TEXT,
        telegram_sent INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(position_id) REFERENCES positions(id)
      );
      CREATE INDEX IF NOT EXISTS idx_position_alerts_position ON position_alerts(position_id);
      CREATE INDEX IF NOT EXISTS idx_position_alerts_time ON position_alerts(alert_time);
    `);
  }

  private async createSimulatedAccountsTable() {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS simulated_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_name TEXT UNIQUE NOT NULL,
        initial_balance REAL NOT NULL,
        current_balance REAL NOT NULL,
        total_trades INTEGER DEFAULT 0,
        winning_trades INTEGER DEFAULT 0,
        losing_trades INTEGER DEFAULT 0,
        total_pnl REAL DEFAULT 0,
        win_rate REAL DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
    `);
  }

  private async createSimulatedTradesTable() {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS simulated_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,
        entry_price REAL NOT NULL,
        exit_price REAL,
        quantity REAL NOT NULL,
        entry_time TEXT NOT NULL,
        exit_time TEXT,
        pnl REAL,
        pnl_percent REAL,
        status TEXT DEFAULT 'open',
        strategy TEXT,
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(account_id) REFERENCES simulated_accounts(id)
      );
      CREATE INDEX IF NOT EXISTS idx_simulated_trades_account ON simulated_trades(account_id);
      CREATE INDEX IF NOT EXISTS idx_simulated_trades_symbol ON simulated_trades(symbol);
      CREATE INDEX IF NOT EXISTS idx_simulated_trades_status ON simulated_trades(status);
    `);
  }

  private async createAccountSnapshotsTable() {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS account_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL,
        snapshot_time TEXT NOT NULL,
        balance REAL NOT NULL,
        total_pnl REAL NOT NULL,
        open_positions INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(account_id) REFERENCES simulated_accounts(id)
      );
      CREATE INDEX IF NOT EXISTS idx_snapshots_account ON account_snapshots(account_id);
      CREATE INDEX IF NOT EXISTS idx_snapshots_time ON account_snapshots(snapshot_time);
    `);
  }

  private async createConvergenceStatsTable() {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS convergence_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        timeframe TEXT NOT NULL DEFAULT '5m',
        convergence_time TEXT NOT NULL,
        boll_width REAL NOT NULL,
        boll_width_percent REAL,
        boll_upper REAL,
        boll_middle REAL,
        boll_lower REAL,
        close_price REAL,
        rsi_5min REAL,
        sar_direction TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, timeframe, convergence_time)
      );
      CREATE INDEX IF NOT EXISTS idx_convergence_symbol ON convergence_stats(symbol);
      CREATE INDEX IF NOT EXISTS idx_convergence_time ON convergence_stats(convergence_time);
    `);
  }

  private async createSystemSettingsTable() {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS system_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_key TEXT UNIQUE NOT NULL,
        setting_value TEXT NOT NULL,
        setting_type TEXT DEFAULT 'number',
        display_name TEXT NOT NULL,
        description TEXT,
        category TEXT DEFAULT 'general',
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      CREATE INDEX IF NOT EXISTS idx_settings_category ON system_settings(category);
    `);
  }

  private async createTradingRulesTable() {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS trading_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_name TEXT NOT NULL,
        rule_type TEXT NOT NULL,
        description TEXT,
        enabled INTEGER DEFAULT 1,
        priority INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      CREATE INDEX IF NOT EXISTS idx_trading_rules_enabled ON trading_rules(enabled);
    `);
  }

  private async createTradingStrategiesTable() {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS trading_strategies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_name TEXT NOT NULL,
        strategy_type TEXT NOT NULL,
        description TEXT,
        enabled INTEGER DEFAULT 1,
        priority INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      CREATE INDEX IF NOT EXISTS idx_trading_strategies_enabled ON trading_strategies(enabled);
    `);
  }

  private async createSupportLinesTable() {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS support_lines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        support_price REAL NOT NULL,
        date TEXT NOT NULL,
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, date)
      );
      CREATE INDEX IF NOT EXISTS idx_support_lines_symbol ON support_lines(symbol);
      CREATE INDEX IF NOT EXISTS idx_support_lines_date ON support_lines(date);
    `);
  }

  private async createConsecutiveRiseDominanceTable() {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS consecutive_rise_dominance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL UNIQUE,
        current_streak INTEGER DEFAULT 0,
        max_streak INTEGER DEFAULT 0,
        max_streak_start_time TEXT,
        max_streak_end_time TEXT,
        last_check_time TEXT,
        last_high_ratio REAL,
        last_low_ratio REAL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      CREATE INDEX IF NOT EXISTS idx_consecutive_rise_symbol ON consecutive_rise_dominance(symbol);
      CREATE INDEX IF NOT EXISTS idx_consecutive_rise_max_streak ON consecutive_rise_dominance(max_streak DESC);
      CREATE INDEX IF NOT EXISTS idx_consecutive_rise_current_streak ON consecutive_rise_dominance(current_streak DESC);
    `);
  }
}

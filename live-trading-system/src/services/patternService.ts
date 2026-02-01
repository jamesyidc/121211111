/**
 * 模式特征分析服务
 * 分析K线数据,寻找起涨和起跌模式,提取特征并保存到数据库
 */

export class PatternService {
  private db: D1Database;

  constructor(db: D1Database) {
    this.db = db;
  }

  /**
   * 分析币种的起涨模式（10根K线涨幅>2%）
   */
  async analyzeSurgePatterns(symbol: string, timeframe: string = '5m') {
    console.log(`📈 开始分析 ${symbol} 的起涨模式...`);
    
    // 获取最近600根K线数据
    const result = await this.db
      .prepare(`
        SELECT open_time, open, high, low, close, volume, volume_v1, volume_v2
        FROM kline_data
        WHERE symbol = ? AND timeframe = ?
        ORDER BY open_time ASC
        LIMIT 600
      `)
      .bind(symbol, timeframe)
      .all();
    
    const klines: any[] = result.results;
    if (klines.length < 10) {
      console.log(`  ⚠️  ${symbol} K线数据不足，跳过`);
      return [];
    }
    
    const patterns = [];
    
    // 滑动窗口扫描，每次看10根K线
    for (let i = 0; i <= klines.length - 10; i++) {
      const window = klines.slice(i, i + 10);
      
      // 计算10根K线的总涨跌幅
      const startPrice = window[0].open;
      const endPrice = window[9].close;
      const totalChange = ((endPrice - startPrice) / startPrice) * 100;
      
      // 如果总涨幅 >= 2%，记录这个模式
      if (totalChange >= 2) {
        const features = this.extractSurgeFeatures(window);
        patterns.push({
          symbol,
          start_time: window[0].open_time,
          end_time: window[9].open_time,
          total_change: totalChange,
          kline_count: 10,
          features
        });
      }
    }
    
    console.log(`  ✅ ${symbol} 找到 ${patterns.length} 个起涨模式`);
    return patterns;
  }

  /**
   * 分析币种的起跌模式（10根K线跌幅>3%）
   */
  async analyzeCrashPatterns(symbol: string, timeframe: string = '5m') {
    console.log(`📉 开始分析 ${symbol} 的起跌模式...`);
    
    // 获取最近600根K线数据
    const result = await this.db
      .prepare(`
        SELECT open_time, open, high, low, close, volume, volume_v1, volume_v2
        FROM kline_data
        WHERE symbol = ? AND timeframe = ?
        ORDER BY open_time ASC
        LIMIT 600
      `)
      .bind(symbol, timeframe)
      .all();
    
    const klines: any[] = result.results;
    if (klines.length < 10) {
      console.log(`  ⚠️  ${symbol} K线数据不足，跳过`);
      return [];
    }
    
    const patterns = [];
    
    // 滑动窗口扫描，每次看10根K线
    for (let i = 0; i <= klines.length - 10; i++) {
      const window = klines.slice(i, i + 10);
      
      // 计算10根K线的总涨跌幅
      const startPrice = window[0].open;
      const endPrice = window[9].close;
      const totalChange = ((endPrice - startPrice) / startPrice) * 100;
      
      // 如果总跌幅 <= -3%，记录这个模式
      if (totalChange <= -3) {
        const features = this.extractCrashFeatures(window);
        patterns.push({
          symbol,
          start_time: window[0].open_time,
          end_time: window[9].open_time,
          total_change: totalChange,
          kline_count: 10,
          features
        });
      }
    }
    
    console.log(`  ✅ ${symbol} 找到 ${patterns.length} 个起跌模式`);
    return patterns;
  }

  /**
   * 提取起涨特征
   */
  private extractSurgeFeatures(window: any[]) {
    // 1. 成交量特征
    const volumeV1Count = window.filter(k => k.volume_v1 === 1).length;
    const volumeV2Count = window.filter(k => k.volume_v2 === 1).length;
    const hasVolumeV1 = volumeV1Count > 0;
    const avgVolume = window.reduce((sum, k) => sum + k.volume, 0) / window.length;
    const maxVolume = Math.max(...window.map(k => k.volume));
    const volumeSurge = maxVolume / avgVolume;
    
    // 2. 价格形态特征
    const greenCount = window.filter(k => k.close > k.open).length; // 阳线数量
    const redCount = window.filter(k => k.close < k.open).length;   // 阴线数量
    const continuousGreen = this.countContinuous(window, 'green');
    
    // 3. 涨跌幅分布
    const changes = window.map((k, i) => {
      if (i === 0) return 0;
      return ((k.close - window[i-1].close) / window[i-1].close) * 100;
    });
    const maxSingleChange = Math.max(...changes);
    const avgChange = changes.reduce((a, b) => a + b, 0) / changes.length;
    
    // 4. 价格突破特征
    const startPrice = window[0].open;
    const maxPrice = Math.max(...window.map(k => k.high));
    const breakoutPercent = ((maxPrice - startPrice) / startPrice) * 100;
    
    // 5. 起涨初期特征（前3根K线）
    const earlyPhase = window.slice(0, 3);
    const earlyVolumeSurge = earlyPhase.some(k => k.volume_v1 === 1 || k.volume_v2 === 1);
    const earlyGreenCount = earlyPhase.filter(k => k.close > k.open).length;
    const earlyChange = ((earlyPhase[2].close - earlyPhase[0].open) / earlyPhase[0].open) * 100;
    
    return {
      // 成交量特征
      volume_v1_count: volumeV1Count,
      volume_v2_count: volumeV2Count,
      has_volume_v1: hasVolumeV1,
      volume_surge_ratio: volumeSurge.toFixed(2),
      
      // 形态特征
      green_count: greenCount,
      red_count: redCount,
      continuous_green: continuousGreen,
      
      // 涨幅特征
      max_single_change: maxSingleChange.toFixed(2),
      avg_change: avgChange.toFixed(2),
      breakout_percent: breakoutPercent.toFixed(2),
      
      // 起涨初期特征
      early_volume_surge: earlyVolumeSurge,
      early_green_count: earlyGreenCount,
      early_change: earlyChange.toFixed(2)
    };
  }

  /**
   * 提取起跌特征
   */
  private extractCrashFeatures(window: any[]) {
    // 1. 成交量特征
    const volumeV1Count = window.filter(k => k.volume_v1 === 1).length;
    const volumeV2Count = window.filter(k => k.volume_v2 === 1).length;
    const hasVolumeV1 = volumeV1Count > 0;
    const avgVolume = window.reduce((sum, k) => sum + k.volume, 0) / window.length;
    const maxVolume = Math.max(...window.map(k => k.volume));
    const volumeSurge = maxVolume / avgVolume;
    
    // 2. 价格形态特征
    const greenCount = window.filter(k => k.close > k.open).length; // 阳线数量
    const redCount = window.filter(k => k.close < k.open).length;   // 阴线数量
    const continuousRed = this.countContinuous(window, 'red');
    
    // 3. 涨跌幅分布
    const changes = window.map((k, i) => {
      if (i === 0) return 0;
      return ((k.close - window[i-1].close) / window[i-1].close) * 100;
    });
    const minSingleChange = Math.min(...changes);
    const avgChange = changes.reduce((a, b) => a + b, 0) / changes.length;
    
    // 4. 价格跌破特征
    const startPrice = window[0].open;
    const minPrice = Math.min(...window.map(k => k.low));
    const crashPercent = ((minPrice - startPrice) / startPrice) * 100;
    
    // 5. 起跌初期特征（前3根K线）
    const earlyPhase = window.slice(0, 3);
    const earlyVolumeSurge = earlyPhase.some(k => k.volume_v1 === 1 || k.volume_v2 === 1);
    const earlyRedCount = earlyPhase.filter(k => k.close < k.open).length;
    const earlyChange = ((earlyPhase[2].close - earlyPhase[0].open) / earlyPhase[0].open) * 100;
    
    return {
      // 成交量特征
      volume_v1_count: volumeV1Count,
      volume_v2_count: volumeV2Count,
      has_volume_v1: hasVolumeV1,
      volume_surge_ratio: volumeSurge.toFixed(2),
      
      // 形态特征
      green_count: greenCount,
      red_count: redCount,
      continuous_red: continuousRed,
      
      // 跌幅特征
      min_single_change: minSingleChange.toFixed(2),
      avg_change: avgChange.toFixed(2),
      crash_percent: crashPercent.toFixed(2),
      
      // 起跌初期特征
      early_volume_surge: earlyVolumeSurge,
      early_red_count: earlyRedCount,
      early_change: earlyChange.toFixed(2)
    };
  }

  /**
   * 计算连续同向K线数量
   */
  private countContinuous(window: any[], type: 'green' | 'red'): number {
    let maxContinuous = 0;
    let currentContinuous = 0;
    
    for (const k of window) {
      const isTarget = type === 'green' 
        ? k.close > k.open 
        : k.close < k.open;
      
      if (isTarget) {
        currentContinuous++;
        maxContinuous = Math.max(maxContinuous, currentContinuous);
      } else {
        currentContinuous = 0;
      }
    }
    
    return maxContinuous;
  }

  /**
   * 保存模式特征到数据库
   */
  async savePattern(patternType: 'surge' | 'crash', pattern: any) {
    const featuresJson = JSON.stringify(pattern.features);
    
    // 提取关键特征作为独立字段
    const volumeSurge = pattern.features.volume_v1_count > 0 ? 1 : 0;
    const priceBreakout = patternType === 'surge' 
      ? parseFloat(pattern.features.breakout_percent) > 3
      : parseFloat(pattern.features.crash_percent) < -4;
    const continuousDirection = patternType === 'surge'
      ? pattern.features.continuous_green >= 5
      : pattern.features.continuous_red >= 5;
    
    await this.db
      .prepare(`
        INSERT OR REPLACE INTO pattern_features (
          pattern_type, symbol, start_time, end_time, total_change, kline_count,
          features, volume_surge, price_breakout, continuous_direction
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `)
      .bind(
        patternType,
        pattern.symbol,
        pattern.start_time,
        pattern.end_time,
        pattern.total_change,
        pattern.kline_count,
        featuresJson,
        volumeSurge,
        priceBreakout ? 1 : 0,
        continuousDirection ? 1 : 0
      )
      .run();
  }

  /**
   * 获取所有起涨模式
   */
  async getSurgePatterns(limit: number = 100) {
    const result = await this.db
      .prepare(`
        SELECT * FROM pattern_features
        WHERE pattern_type = 'surge'
        ORDER BY start_time DESC
        LIMIT ?
      `)
      .bind(limit)
      .all();
    
    return result.results.map((r: any) => ({
      ...r,
      features: JSON.parse(r.features)
    }));
  }

  /**
   * 获取所有起跌模式
   */
  async getCrashPatterns(limit: number = 100) {
    const result = await this.db
      .prepare(`
        SELECT * FROM pattern_features
        WHERE pattern_type = 'crash'
        ORDER BY start_time DESC
        LIMIT ?
      `)
      .bind(limit)
      .all();
    
    return result.results.map((r: any) => ({
      ...r,
      features: JSON.parse(r.features)
    }));
  }

  /**
   * 获取特征统计摘要
   */
  async getPatternStats() {
    const surgeResult = await this.db
      .prepare(`
        SELECT 
          COUNT(*) as total,
          AVG(total_change) as avg_change,
          SUM(volume_surge) as volume_surge_count,
          SUM(price_breakout) as breakout_count,
          SUM(continuous_direction) as continuous_count
        FROM pattern_features
        WHERE pattern_type = 'surge'
      `)
      .first();
    
    const crashResult = await this.db
      .prepare(`
        SELECT 
          COUNT(*) as total,
          AVG(total_change) as avg_change,
          SUM(volume_surge) as volume_surge_count,
          SUM(price_breakout) as breakout_count,
          SUM(continuous_direction) as continuous_count
        FROM pattern_features
        WHERE pattern_type = 'crash'
      `)
      .first();
    
    return {
      surge: surgeResult,
      crash: crashResult
    };
  }
}

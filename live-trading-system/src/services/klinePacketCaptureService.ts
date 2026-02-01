/**
 * K线数据抓包服务
 * 功能：自动抓取K线数据并存储到数据库
 * 时间点：每5分钟在特定秒数执行（52, 57, 02, 07, 12, 17, 22, 27秒）
 */

interface KlinePacketData {
  symbol: string;
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  turnover: number;
  // 添加图片中显示的其他字段
  涨跌额?: number;
  涨跌幅?: number;
  幅度?: number;
  成交量?: string;
  成交额?: string;
  换手率?: number;
  市盈率?: number;
  市净率?: number;
  总市值?: string;
  流通市值?: string;
}

interface CaptureConfig {
  enabled: boolean;
  intervalMinutes: number; // 间隔分钟数（默认5分钟）
  captureSeconds: number[]; // 执行的秒数列表
  sourceUrl: string; // 数据源URL
  symbols: string[]; // 要抓取的币种列表
}

export class KlinePacketCaptureService {
  private db: D1Database;
  private config: CaptureConfig;
  private timerId: NodeJS.Timeout | null = null;
  private isRunning: boolean = false;
  private nextExecutionTime: Date | null = null;

  constructor(db: D1Database, config: Partial<CaptureConfig> = {}) {
    this.db = db;
    this.config = {
      enabled: config.enabled ?? true,
      intervalMinutes: config.intervalMinutes ?? 5,
      captureSeconds: config.captureSeconds ?? [52, 57, 2, 7, 12, 17, 22, 27],
      sourceUrl: config.sourceUrl ?? 'https://api.example.com/kline',
      symbols: config.symbols ?? ['BTC', 'ETH', 'XRP', 'BNB', 'SOL']
    };
  }

  /**
   * 计算下一次执行时间
   * @returns {delay: 毫秒延迟, nextTime: 下次执行时间}
   */
  private calculateNextExecution(): { delay: number; nextTime: Date; remainingTime: string } {
    const now = new Date();
    const currentMinutes = now.getMinutes();
    const currentSeconds = now.getSeconds();
    const currentMilliseconds = now.getMilliseconds();
    
    const { intervalMinutes, captureSeconds } = this.config;
    
    // 对秒数进行排序
    const sortedSeconds = [...captureSeconds].sort((a, b) => a - b);
    
    // 计算当前是在哪个周期内
    const currentCycle = Math.floor(currentMinutes / intervalMinutes);
    
    // 找到下一个应该执行的秒数
    let nextSecond: number | null = null;
    let nextMinute = currentMinutes;
    
    // 首先在当前分钟内查找
    for (const second of sortedSeconds) {
      if (currentMinutes % intervalMinutes === 0 && second > currentSeconds) {
        nextSecond = second;
        break;
      }
    }
    
    // 如果当前分钟内没有找到，则找下一个周期的第一个秒数
    if (nextSecond === null) {
      nextMinute = (currentCycle + 1) * intervalMinutes;
      nextSecond = sortedSeconds[0];
    }
    
    // 处理跨小时的情况
    const nextHour = nextMinute >= 60 ? 1 : 0;
    nextMinute = nextMinute % 60;
    
    // 创建下一次执行的时间
    const nextExecution = new Date(now);
    nextExecution.setHours(now.getHours() + nextHour);
    nextExecution.setMinutes(nextMinute);
    nextExecution.setSeconds(nextSecond);
    nextExecution.setMilliseconds(0);
    
    // 计算延迟毫秒数
    let delay = nextExecution.getTime() - now.getTime();
    
    // 如果计算出的延迟为负数或非常小，说明需要等到下一个周期
    if (delay <= 0) {
      const nextSecondIndex = sortedSeconds.indexOf(nextSecond);
      if (nextSecondIndex < sortedSeconds.length - 1) {
        // 使用同一分钟内的下一个秒数
        nextExecution.setSeconds(sortedSeconds[nextSecondIndex + 1]);
      } else {
        // 使用下一个周期的第一个秒数
        nextExecution.setMinutes(nextExecution.getMinutes() + intervalMinutes);
        nextExecution.setSeconds(sortedSeconds[0]);
      }
      delay = nextExecution.getTime() - now.getTime();
    }
    
    // 计算剩余时间字符串
    const remainingSeconds = Math.floor(delay / 1000);
    const minutes = Math.floor(remainingSeconds / 60);
    const seconds = remainingSeconds % 60;
    const remainingTime = `${minutes}分${seconds}秒`;
    
    return { delay, nextTime: nextExecution, remainingTime };
  }

  /**
   * 启动自动抓取
   */
  start(): void {
    if (!this.config.enabled) {
      console.log('📅 K线数据抓包已禁用');
      return;
    }

    if (this.isRunning) {
      console.log('⚠️  K线数据抓包已在运行中');
      return;
    }

    this.isRunning = true;
    console.log(`🚀 启动K线数据自动抓包`);
    console.log(`⏱️  配置: 每${this.config.intervalMinutes}分钟在 ${this.config.captureSeconds.join(', ')} 秒执行`);
    
    this.scheduleNext();
  }

  /**
   * 安排下一次执行
   */
  private scheduleNext(): void {
    if (!this.isRunning) {
      return;
    }

    const { delay, nextTime, remainingTime } = this.calculateNextExecution();
    this.nextExecutionTime = nextTime;
    
    const nextTimeString = nextTime.toLocaleString('zh-CN', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
    
    console.log(`⏳ 下次抓取时间: ${nextTimeString} (剩余: ${remainingTime})`);

    this.timerId = setTimeout(async () => {
      await this.executeCapture();
      this.scheduleNext(); // 执行完后安排下一次
    }, delay);
  }

  /**
   * 停止自动抓取
   */
  stop(): void {
    if (this.timerId) {
      clearTimeout(this.timerId);
      this.timerId = null;
      this.isRunning = false;
      this.nextExecutionTime = null;
      console.log('🛑 K线数据抓包已停止');
    }
  }

  /**
   * 执行抓取
   */
  private async executeCapture(): Promise<void> {
    const now = new Date();
    const startTime = Date.now();
    const timeString = now.toLocaleString('zh-CN', { 
      hour12: false,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
    
    console.log(`\n📦 [${timeString}] 开始抓取K线数据...`);

    try {
      const results = [];
      
      // 抓取所有配置的币种
      for (const symbol of this.config.symbols) {
        try {
          const data = await this.fetchKlineData(symbol);
          await this.saveToDatabase(symbol, data, now.getTime());
          results.push({ symbol, success: true });
        } catch (error: any) {
          console.error(`❌ ${symbol} 抓取失败:`, error.message);
          results.push({ symbol, success: false, error: error.message });
        }
      }
      
      const duration = ((Date.now() - startTime) / 1000).toFixed(2);
      const successCount = results.filter(r => r.success).length;
      const failCount = results.length - successCount;
      
      console.log(`✅ K线数据抓取完成 (耗时: ${duration}秒)`);
      console.log(`   - 成功: ${successCount} 个币种`);
      console.log(`   - 失败: ${failCount} 个币种`);
      
    } catch (error: any) {
      const duration = ((Date.now() - startTime) / 1000).toFixed(2);
      console.error(`❌ K线数据抓取异常 (耗时: ${duration}秒):`, error.message);
    }
  }

  /**
   * 从数据源获取K线数据
   */
  private async fetchKlineData(symbol: string): Promise<KlinePacketData> {
    // 这里需要根据实际的API接口实现
    // 示例：从OKX或其他交易所API获取数据
    const url = `${this.config.sourceUrl}?symbol=${symbol}`;
    
    const response = await fetch(url, {
      headers: {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0'
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    
    // 根据实际API响应格式解析数据
    return this.parseKlineData(symbol, data);
  }

  /**
   * 解析K线数据
   */
  private parseKlineData(symbol: string, rawData: any): KlinePacketData {
    // 根据实际API响应格式进行解析
    // 这是一个示例，需要根据实际情况调整
    return {
      symbol,
      timestamp: Date.now(),
      open: parseFloat(rawData.open || '0'),
      high: parseFloat(rawData.high || '0'),
      low: parseFloat(rawData.low || '0'),
      close: parseFloat(rawData.close || '0'),
      volume: parseFloat(rawData.volume || '0'),
      turnover: parseFloat(rawData.turnover || '0'),
      涨跌额: parseFloat(rawData.change || '0'),
      涨跌幅: parseFloat(rawData.changePercent || '0'),
      幅度: parseFloat(rawData.amplitude || '0'),
      成交量: rawData.volume,
      成交额: rawData.turnover,
      换手率: parseFloat(rawData.turnoverRate || '0'),
      市盈率: parseFloat(rawData.pe || '0'),
      市净率: parseFloat(rawData.pb || '0'),
      总市值: rawData.totalMarketCap,
      流通市值: rawData.circulatingMarketCap
    };
  }

  /**
   * 保存到数据库（按时间倒序）
   */
  private async saveToDatabase(symbol: string, data: KlinePacketData, captureTime: number): Promise<void> {
    await this.db
      .prepare(`
        INSERT INTO kline_packet_capture (
          symbol,
          capture_time,
          timestamp,
          open,
          high,
          low,
          close,
          volume,
          turnover,
          change_amount,
          change_percent,
          amplitude,
          volume_str,
          turnover_str,
          turnover_rate,
          pe_ratio,
          pb_ratio,
          total_market_cap,
          circulating_market_cap,
          created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `)
      .bind(
        symbol,
        captureTime,
        data.timestamp,
        data.open,
        data.high,
        data.low,
        data.close,
        data.volume,
        data.turnover,
        data.涨跌额 || 0,
        data.涨跌幅 || 0,
        data.幅度 || 0,
        data.成交量 || '',
        data.成交额 || '',
        data.换手率 || 0,
        data.市盈率 || 0,
        data.市净率 || 0,
        data.总市值 || '',
        data.流通市值 || '',
        Date.now()
      )
      .run();
    
    console.log(`💾 ${symbol} 数据已保存到数据库`);
  }

  /**
   * 查询历史抓包数据（按时间倒序）
   */
  async getHistoryData(symbol?: string, limit: number = 100): Promise<any[]> {
    let query = `
      SELECT * FROM kline_packet_capture
    `;
    
    const params: any[] = [];
    
    if (symbol) {
      query += ` WHERE symbol = ?`;
      params.push(symbol);
    }
    
    query += ` ORDER BY capture_time DESC LIMIT ?`;
    params.push(limit);
    
    const result = await this.db
      .prepare(query)
      .bind(...params)
      .all();
    
    return result.results || [];
  }

  /**
   * 获取剩余时间（用于前端显示）
   */
  getRemainingTime(): { remainingTime: string; nextExecutionTime: string | null } {
    if (!this.isRunning || !this.nextExecutionTime) {
      return { remainingTime: '--', nextExecutionTime: null };
    }
    
    const now = Date.now();
    const delay = this.nextExecutionTime.getTime() - now;
    
    if (delay <= 0) {
      return { remainingTime: '即将执行...', nextExecutionTime: null };
    }
    
    const remainingSeconds = Math.floor(delay / 1000);
    const minutes = Math.floor(remainingSeconds / 60);
    const seconds = remainingSeconds % 60;
    const remainingTime = `${minutes}分${seconds}秒`;
    
    const nextTimeString = this.nextExecutionTime.toLocaleString('zh-CN', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
    
    return { remainingTime, nextExecutionTime: nextTimeString };
  }

  /**
   * 立即执行一次抓取（手动触发）
   */
  async captureNow(): Promise<void> {
    console.log('🔄 手动触发K线数据抓取...');
    await this.executeCapture();
  }

  /**
   * 获取运行状态
   */
  getStatus(): {
    isRunning: boolean;
    config: CaptureConfig;
    nextExecutionTime: string | null;
    remainingTime: string;
  } {
    const { remainingTime, nextExecutionTime } = this.getRemainingTime();
    
    return {
      isRunning: this.isRunning,
      config: { ...this.config },
      nextExecutionTime,
      remainingTime
    };
  }
}

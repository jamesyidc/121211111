import { IndicatorService } from './indicatorService';
import { isVolumeAboveV1, isVolumeAboveV2 } from '../config/volumeThresholds';
import { KlineDbGuard } from './klineDbGuard';

export class KlineService {
  private db: D1Database;
  private indicatorService: IndicatorService;

  constructor(db: D1Database) {
    this.db = db;
    this.indicatorService = new IndicatorService();
    
    // 🔒 声明此服务有K线数据写入权限
    KlineDbGuard.checkWritePermission('KlineService');
  }

  // 从 OKX 获取 K线数据
  async fetchKlineFromOKX(okxSymbol: string, timeframe: string = '5m', limit: number = 300) {
    const url = `https://www.okx.com/api/v5/market/candles?instId=${okxSymbol}&bar=${timeframe}&limit=${limit}`;
    
    const response = await fetch(url, {
      headers: {
        'Accept': 'application/json',
      }
    });

    if (!response.ok) {
      throw new Error(`OKX API error: ${response.status}`);
    }

    const data = await response.json();
    
    if (data.code !== '0') {
      throw new Error(`OKX API error: ${data.msg}`);
    }

    return data.data; // 返回 K线数组
  }

  // 保存 K线数据 (优化：使用批量插入)
  async saveKlineData(symbol: string, timeframe: string, klineArray: any[]) {
    if (klineArray.length === 0) return;
    
    // 使用 D1 batch API 批量插入
    const statements = klineArray.map((kline) => {
      // OKX K线格式: [timestamp, open, high, low, close, volume, volumeCcy, volCcyQuote, confirm]
      const [openTime, open, high, low, close, volume, volumeCcy, volCcyQuote] = kline;
      
      const vol = parseFloat(volume);
      const v1 = isVolumeAboveV1(symbol, vol) ? 1 : 0;
      const v2 = isVolumeAboveV2(symbol, vol) ? 1 : 0;
      
      return this.db.prepare(`
        INSERT INTO kline_data (
          symbol, timeframe, open_time, open, high, low, close, volume,
          quote_volume, trades_count, volume_v1, volume_v2
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, timeframe, open_time) 
        DO UPDATE SET
          open = excluded.open,
          high = excluded.high,
          low = excluded.low,
          close = excluded.close,
          volume = excluded.volume,
          quote_volume = excluded.quote_volume,
          volume_v1 = excluded.volume_v1,
          volume_v2 = excluded.volume_v2
      `).bind(
        symbol,
        timeframe,
        parseInt(openTime),
        parseFloat(open),
        parseFloat(high),
        parseFloat(low),
        parseFloat(close),
        vol,
        parseFloat(volCcyQuote || '0'),
        0, // OKX 不提供交易次数
        v1,
        v2
      );
    });
    
    // 批量执行
    await this.db.batch(statements);
  }

  // 获取币种的 K线数据
  async getKlineData(symbol: string, timeframe: string, limit: number = 100) {
    const result = await this.db
      .prepare(`
        SELECT * FROM kline_data 
        WHERE symbol = ? AND timeframe = ?
        ORDER BY open_time DESC 
        LIMIT ?
      `)
      .bind(symbol, timeframe, limit)
      .all();
    
    return result.results;
  }

  // 获取最新的 K线时间
  async getLatestKlineTime(symbol: string, timeframe: string) {
    const result = await this.db
      .prepare(`
        SELECT MAX(open_time) as latest_time 
        FROM kline_data 
        WHERE symbol = ? AND timeframe = ?
      `)
      .bind(symbol, timeframe)
      .first();
    
    return result?.latest_time || 0;
  }

  // 获取 OKX 配置
  async getOKXConfig(symbol: string) {
    const result = await this.db
      .prepare('SELECT * FROM okx_config WHERE symbol = ?')
      .bind(symbol)
      .first();
    
    return result;
  }

  // 获取所有 OKX 配置
  async getAllOKXConfigs() {
    const result = await this.db
      .prepare('SELECT * FROM okx_config')
      .all();
    
    return result.results;
  }

  // 同步所有币种的 K线数据 (优化：添加延迟避免速率限制)
  async syncAllKlineData(timeframe: string = '5m', limit: number = 300) {
    const configs: any = await this.getAllOKXConfigs();
    const results = [];

    for (let i = 0; i < configs.length; i++) {
      const config = configs[i];
      try {
        const klineData = await this.fetchKlineFromOKX(config.okx_symbol, timeframe, limit);
        
        // 🔥 过滤掉 confirm=0 的未完成K线（OKX格式第9个字段）
        const confirmedKlines = klineData.filter((k: any) => k[8] === '1');
        
        // 🔥 只保存已确认的K线
        await this.saveKlineData(config.symbol, timeframe, confirmedKlines);
        
        // 🆕 清理60天以前的旧数据（保留60天 = 17280条5分钟K线）
        await this.cleanOldKlineDataByDays(config.symbol, timeframe, 60);
        
        results.push({
          symbol: config.symbol,
          success: true,
          count: confirmedKlines.length,
          total: klineData.length,
          filtered: klineData.length - confirmedKlines.length
        });
        
        // 避免OKX API速率限制：每请求后延迟100ms
        if (i < configs.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 100));
        }
      } catch (error: any) {
        results.push({
          symbol: config.symbol,
          success: false,
          error: error.message
        });
      }
    }

    return results;
  }

  // 计算 K线统计信息
  async getKlineStats(symbol: string, timeframe: string, limit: number = 100) {
    const klines: any = await this.getKlineData(symbol, timeframe, limit);
    
    if (klines.length === 0) {
      return null;
    }

    // 计算涨跌幅
    const latest = klines[0]; // 最新的K线（第1根）
    const oldest = klines[klines.length - 1];
    const changePercent = ((latest.close - oldest.open) / oldest.open) * 100;

    // 🔥 从所有K线中计算最高最低价
    let highest = klines[0].high;
    let lowest = klines[0].low;
    let totalVolume = 0;

    for (const kline of klines) {
      if (kline.high > highest) highest = kline.high;
      if (kline.low < lowest) lowest = kline.low;
      totalVolume += kline.volume;
    }

    // 🔥 只判断当前K线（第1根）是否创新高/新低
    // 不判断历史K线（2-10根），保持它们原有的结果
    const isNewHigh = latest.high >= highest; // 当前K线的最高价是否是这10根中的最高
    const isNewLow = latest.low <= lowest;    // 当前K线的最低价是否是这10根中的最低

    return {
      symbol,
      timeframe,
      dataCount: klines.length,
      latestPrice: latest.close,
      latestTime: latest.open_time,
      latestHigh: latest.high,
      latestLow: latest.low,
      changePercent,
      highest,        // 10根K线中的最高价
      lowest,         // 10根K线中的最低价
      isNewHigh,      // 当前K线是否创新高
      isNewLow,       // 当前K线是否创新低
      totalVolume,
      avgVolume: totalVolume / klines.length
    };
  }

  // 获取多个时间周期的数据
  async getMultiTimeframeData(symbol: string) {
    const timeframes = ['5m', '15m', '1H', '4H', '1D'];
    const results: any = {};

    for (const tf of timeframes) {
      const stats = await this.getKlineStats(symbol, tf, 100);
      if (stats) {
        results[tf] = stats;
      }
    }

    return results;
  }

  // 删除旧数据（保留最近N条）
  async cleanOldKlineData(symbol: string, timeframe: string, keepCount: number = 1000) {
    await this.db
      .prepare(`
        DELETE FROM kline_data 
        WHERE symbol = ? AND timeframe = ? 
        AND open_time < (
          SELECT open_time FROM kline_data 
          WHERE symbol = ? AND timeframe = ?
          ORDER BY open_time DESC 
          LIMIT 1 OFFSET ?
        )
      `)
      .bind(symbol, timeframe, symbol, timeframe, keepCount)
      .run();
  }

  // 🆕 按天数清理旧数据（保留最近N天）
  async cleanOldKlineDataByDays(symbol: string, timeframe: string, keepDays: number = 30) {
    // 计算N天前的时间戳（毫秒）
    const cutoffTime = Date.now() - (keepDays * 24 * 60 * 60 * 1000);
    
    await this.db
      .prepare(`
        DELETE FROM kline_data 
        WHERE symbol = ? AND timeframe = ? 
        AND open_time < ?
      `)
      .bind(symbol, timeframe, cutoffTime)
      .run();
  }

  // 获取带技术指标的 K线数据
  async getKlineWithIndicators(symbol: string, timeframe: string = '5m', limit: number = 300) {
    // 为了确保所有返回的K线都有完整的指标值，需要获取额外的历史数据
    // BOLL 需要 20 个周期，RSI 需要 14 个周期，为安全起见，额外获取 50 根K线
    const EXTRA_BARS = 50;
    const fetchLimit = limit + EXTRA_BARS;
    
    // 先尝试从数据库获取（获取比需要更多的数据）
    const dbData: any = await this.getKlineData(symbol, timeframe, fetchLimit);
    
    let klineData: any[];
    let dbIndicators: Map<number, any> = new Map(); // 存储数据库中的所有技术指标
    
    // 🔥 强制重新计算所有技术指标（不使用数据库缓存）
    // 这样确保每次查询都是最新的实时计算结果
    const shouldRecalculateAll = true;
    
    // 优先使用数据库数据（只要有数据就用，不要求数量）
    if (dbData && dbData.length > 50) {
      // 保存数据库中的所有技术指标（按open_time索引）
      dbData.forEach((k: any) => {
        dbIndicators.set(k.open_time, {
          signal: k.signal,
          operation_tip: k.operation_tip,
          channel_state: k.channel_state,
          sar: k.sar,
          sar_change: k.sar_change,
          sar_change_percent: k.sar_change_percent,
          rsi_5min: k.rsi_5min,
          rsi_1h: k.rsi_1h,
          change_percent: k.change_percent,
          change_diff: k.change_diff,
          boll_mb: k.boll_mb,
          boll_ub: k.boll_ub,
          boll_lb: k.boll_lb,
          boll_sar_diff: k.boll_sar_diff,
          boll_angle_mb: k.boll_angle_mb,
          boll_width_change: k.boll_width_change,
          up_channel_exhaustion_ratio: k.up_channel_exhaustion_ratio,
          down_channel_exhaustion_ratio: k.down_channel_exhaustion_ratio,
          volume_level: k.volume_level
        });
      });
      
      // 数据库中有足够的数据，转换格式为 OKX 格式
      // OKX 格式: [timestamp, open, high, low, close, volume, ...]
      // 同时保留 volume_v1 和 volume_v2 标注
      klineData = dbData.reverse().map((k: any) => {
        const arr: any = [
          k.open_time.toString(),
          k.open.toString(),
          k.high.toString(),
          k.low.toString(),
          k.close.toString(),
          k.volume.toString()
        ];
        // 将 volume_v1 和 volume_v2 附加到数组对象上
        arr.volume_v1 = k.volume_v1;
        arr.volume_v2 = k.volume_v2;
        return arr;
      });
    } else {
      // 数据库数据不足，从 OKX 获取
      const config: any = await this.getOKXConfig(symbol);
      if (!config) {
        throw new Error(`未找到 ${symbol} 的 OKX 配置`);
      }
      klineData = await this.fetchKlineFromOKX(config.okx_symbol, timeframe, fetchLimit);
    }
    
    // 计算技术指标（使用所有获取的数据）
    const indicators = this.indicatorService.calculateSARRSIBoll(klineData, symbol);

    // 只返回用户请求的数量（最新的 limit 根K线）
    // indicators 数组是从旧到新排列（因为输入的 klineData 已经 reverse 过）
    // slice(-limit) 取最后 N 条（最新的数据）
    let trimmedIndicators = indicators.slice(-limit);
    
    // ===== 关键修改：反转为从新到旧排列 =====
    // 前端和用户期望看到的是：最新的K线在序号0，越往下时间越早
    // 所以需要将数组反转：从[旧...新]变成[新...旧]
    trimmedIndicators = trimmedIndicators.reverse();
    
    // 重新计算 index，从 0 开始递增
    // 现在 index=0 是最新时间，index 越大时间越早
    // 🆕 优先使用数据库中持久化存储的所有技术指标（如果存在）
    // 🔥 但如果是10格查询(limit<=10)，则强制使用重新计算的值
    trimmedIndicators = trimmedIndicators.map((item, idx) => {
      // item.time 格式: "2025/10/30 00:00:00"
      // 需要转换为时间戳以匹配数据库的 open_time
      const timeStr = item.time.replace(/\//g, '-').replace(' ', 'T') + 'Z';
      const timestamp = new Date(timeStr).getTime();
      const dbData = dbIndicators.get(timestamp);
      
      // 辅助函数：优先使用数据库值，如果不存在或为null则使用计算值
      // 🔥 如果shouldRecalculateAll=true（10格查询），则强制使用计算值
      const getDbValue = (dbVal: any, calcVal: any) => {
        if (shouldRecalculateAll) {
          return calcVal; // 10格查询：强制使用重新计算的值
        }
        return (dbVal !== null && dbVal !== undefined && dbVal !== 'null') ? dbVal : calcVal;
      };
      
      return {
        ...item,
        index: idx,
        // 基础标记字段
        signal: getDbValue(dbData?.signal, item.signal),
        operation_tip: getDbValue(dbData?.operation_tip, null),
        channel_state: getDbValue(dbData?.channel_state, item.channel_state),
        // SAR 指标
        sar: getDbValue(dbData?.sar, item.sar),
        sarChange: getDbValue(dbData?.sar_change, item.sarChange),
        sarChangePercent: getDbValue(dbData?.sar_change_percent, item.sarChangePercent),
        // RSI 指标
        rsi_5min: getDbValue(dbData?.rsi_5min, item.rsi_5min),
        rsi_1h: getDbValue(dbData?.rsi_1h, item.rsi_1h),
        // 涨跌幅
        change: getDbValue(dbData?.change_percent, item.change),
        'change-diff': getDbValue(dbData?.change_diff, item['change-diff']),
        // BOLL 指标
        boll_mb: getDbValue(dbData?.boll_mb, item.boll_mb),
        boll_ub: getDbValue(dbData?.boll_ub, item.boll_ub),
        boll_lb: getDbValue(dbData?.boll_lb, item.boll_lb),
        boll_sar_diff: getDbValue(dbData?.boll_sar_diff, item.boll_sar_diff),
        boll_angle_mb: getDbValue(dbData?.boll_angle_mb, item.boll_angle_mb),
        boll_width_change: getDbValue(dbData?.boll_width_change, item.boll_width_change),
        // 通道衰竭比率
        up_channel_exhaustion_ratio: getDbValue(dbData?.up_channel_exhaustion_ratio, item.up_channel_exhaustion_ratio),
        down_channel_exhaustion_ratio: getDbValue(dbData?.down_channel_exhaustion_ratio, item.down_channel_exhaustion_ratio),
        // 成交量等级
        volume_level: getDbValue(dbData?.volume_level, item.volume_level)
      };
    });

    return {
      symbol,
      timeframe,
      dataCount: trimmedIndicators.length,
      data: trimmedIndicators
    };
  }

  // 批量获取多个币种的技术指标
  async getMultiSymbolIndicators(symbols: string[], timeframe: string = '5m', limit: number = 300) {
    const results: any = {};

    for (const symbol of symbols) {
      try {
        const data = await this.getKlineWithIndicators(symbol, timeframe, limit);
        results[symbol] = {
          success: true,
          data: data
        };
      } catch (error: any) {
        results[symbol] = {
          success: false,
          error: error.message
        };
      }
    }

    return results;
  }

  // 批量获取历史数据（支持超过300根K线）
  async fetchHistoricalKline(okxSymbol: string, timeframe: string = '5m', totalLimit: number = 576) {
    const batchSize = 300; // OKX 单次最大限制
    const batches = Math.ceil(totalLimit / batchSize);
    let allKlines: any[] = [];
    let after: string | null = null; // OKX 分页参数

    for (let i = 0; i < batches; i++) {
      const currentLimit = Math.min(batchSize, totalLimit - allKlines.length);
      
      // 构建 URL
      let url = `https://www.okx.com/api/v5/market/candles?instId=${okxSymbol}&bar=${timeframe}&limit=${currentLimit}`;
      if (after) {
        url += `&after=${after}`;
      }

      const response = await fetch(url, {
        headers: {
          'Accept': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`OKX API error: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.code !== '0') {
        throw new Error(`OKX API error: ${data.msg}`);
      }

      const klines = data.data;
      if (!klines || klines.length === 0) {
        break; // 没有更多数据
      }

      allKlines = allKlines.concat(klines);

      // 设置下一批的 after 参数（最后一根K线的时间戳）
      after = klines[klines.length - 1][0];

      // 达到目标数量后停止
      if (allKlines.length >= totalLimit) {
        break;
      }

      // 避免请求过快，等待一小段时间
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    return allKlines;
  }

  // 同步48小时历史数据（576根5分钟K线）
  async sync48HoursData(symbol: string) {
    const config: any = await this.getOKXConfig(symbol);
    if (!config) {
      throw new Error(`未找到 ${symbol} 的 OKX 配置`);
    }

    console.log(`开始同步 ${symbol} 的48小时数据...`);

    // 获取576根5分钟K线（48小时）
    const klineData = await this.fetchHistoricalKline(config.okx_symbol, '5m', 576);
    
    // 保存到数据库
    await this.saveKlineData(symbol, '5m', klineData);

    console.log(`${symbol} 同步完成，共 ${klineData.length} 根K线`);

    return {
      symbol,
      success: true,
      count: klineData.length
    };
  }

  // 批量同步所有币种的48小时数据
  async syncAll48HoursData() {
    const configs: any = await this.getAllOKXConfigs();
    const results = [];

    for (const config of configs) {
      try {
        const result = await this.sync48HoursData(config.symbol);
        results.push(result);
      } catch (error: any) {
        results.push({
          symbol: config.symbol,
          success: false,
          error: error.message
        });
      }

      // 避免请求过快
      await new Promise(resolve => setTimeout(resolve, 200));
    }

    return results;
  }
}

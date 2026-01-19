// 买卖点识别服务
import { ConvergenceStatsService } from './convergenceStatsService';
import { getBeijingTodayStart } from '../utils/timeUtils';

export class SignalService {
  private db?: D1Database;
  private convergenceService?: ConvergenceStatsService;

  constructor(db?: D1Database) {
    this.db = db;
    if (db) {
      this.convergenceService = new ConvergenceStatsService(db);
    }
  }
  // 识别买卖点信号
  // coinLevel: 币种优先级等级（1-6），用于主升信号判断
  detectTradingSignals(klineData: any[], coinLevel?: number): any {
    if (klineData.length < 30) {
      return { signals: [], stats: null, alerts: [] };
    }

    const signals: any[] = [];
    const alerts: any[] = []; // 新增：预警列表（满足任一触发条件）
    
    // 🆕 先记录所有震荡收敛数据（用于统计分析）
    if (this.convergenceService) {
      for (let i = 0; i < klineData.length; i++) {
        const k = klineData[i];
        // 注意：字段名是 channel_state，不是 channelState
        if (k.channel_state && k.channel_state.includes('震荡收敛') && k.boll_ub && k.boll_mb && k.boll_lb) {
          const bollWidth = k.boll_ub - k.boll_lb;
          const bollWidthPercent = (bollWidth / k.boll_mb) * 100;
          
          this.convergenceService.recordConvergence({
            symbol: k.symbol,
            timeframe: '5m',
            convergence_time: k.time,
            boll_width: bollWidth,
            boll_width_percent: bollWidthPercent,
            boll_upper: k.boll_ub,
            boll_middle: k.boll_mb,
            boll_lower: k.boll_lb,
            close_price: parseFloat(k.close),
            rsi_5min: k.rsi_5min,
            sar_direction: k.signal
          }).catch(err => {
            console.error(`记录${k.symbol}震荡收敛数据失败:`, err);
          });
        }
      }
    }
    
    // 计算成交量平均值（用于V1, V2判断）
    const volumes = klineData.map(k => parseFloat(k.volume || '0'));
    const avgVolume = volumes.reduce((a, b) => a + b, 0) / volumes.length;
    const v1 = avgVolume * 1.5; // V1 = 1.5倍平均量
    const v2 = avgVolume * 1.0; // V2 = 1倍平均量

    // 从第2根开始遍历（需要对比前一根）
    for (let i = 1; i < klineData.length; i++) {
      const current = klineData[i];
      const previous = klineData[i - 1];
      
      // 解析数据
      const currentHigh = parseFloat(current.high);
      const currentLow = parseFloat(current.low);
      const currentOpen = parseFloat(current.open);
      const currentClose = parseFloat(current.close);
      const currentVolume = parseFloat(current.volume || '0');
      
      const prevHigh = parseFloat(previous.high);
      const prevLow = parseFloat(previous.low);
      const prevVolume = parseFloat(previous.volume || '0');
      
      // 计算震荡幅度（波动率）
      const volatility = ((currentHigh - currentLow) / currentLow) * 100;
      
      // 计算上下影线
      const bodyHigh = Math.max(currentOpen, currentClose);
      const bodyLow = Math.min(currentOpen, currentClose);
      const upperShadow = currentHigh - bodyHigh;
      const lowerShadow = bodyLow - currentLow;
      const bodySize = Math.abs(currentClose - currentOpen);
      
      // 长上影线：上影线 > 实体的2倍
      const hasLongUpperShadow = upperShadow > bodySize * 2;
      // 长下影线：下影线 > 实体的2倍
      const hasLongLowerShadow = lowerShadow > bodySize * 2;
      
      // 量能衰减：当前量 < 前一根的30%
      const volumeDecay = currentVolume < prevVolume * 0.3;
      
      // 获取指标数据
      const sarChangePercent = parseFloat(current.sarChangePercent || '0');
      const changePercent = parseFloat(current.change?.replace('%', '') || '0');
      const rsi5min = parseFloat(current.rsi_5min || '50');
      
      // 显著变化：涨跌幅 >= 1%
      const significantChange = Math.abs(changePercent) >= 1;
      
      // ===== 触发条件检测（满足任一即预警） =====
      const triggerConditions: string[] = [];
      
      // 1. 成交量触发：V1 或 V2
      const volumeAboveV1 = currentVolume >= v1;
      const volumeAboveV2 = currentVolume >= v2;
      if (volumeAboveV1) triggerConditions.push('成交量≥V1');
      else if (volumeAboveV2) triggerConditions.push('成交量≥V2');
      
      // 2. 涨跌幅触发：±1%
      const changeUp1Percent = changePercent >= 1;
      const changeDown1Percent = changePercent <= -1;
      if (changeUp1Percent) triggerConditions.push('涨幅≥1%');
      if (changeDown1Percent) triggerConditions.push('跌幅≤-1%');
      
      // 3. 震荡（波动率）触发：±1%
      const volatilityHigh = volatility >= 1;
      if (volatilityHigh) triggerConditions.push('震荡≥1%');
      
      // 如果满足任一触发条件，生成预警
      if (triggerConditions.length > 0) {
        alerts.push({
          symbol: current.symbol,
          time: current.time,
          index: current.index,
          triggers: triggerConditions,
          // K线原始数据
          klineData: {
            open: currentOpen,
            high: currentHigh,
            low: currentLow,
            close: currentClose,
            volume: currentVolume,
            // BOLL指标（使用正确的字段名）
            boll_upper: parseFloat(current.boll_ub || '0'),
            boll_middle: parseFloat(current.boll_mb || '0'),
            boll_lower: parseFloat(current.boll_lb || '0'),
            // 其他指标
            rsi_1h: parseFloat(current.rsi_1h || '0'),
            sar_value: parseFloat(current.sar || '0'),
            sar_direction: current.signal || ''
          },
          data: {
            volume: currentVolume.toFixed(2),
            volumeLevel: volumeAboveV1 ? 'V1+' : volumeAboveV2 ? 'V2+' : 'Normal',
            changePercent: changePercent.toFixed(2) + '%',
            volatility: volatility.toFixed(2) + '%',
            rsi5min: rsi5min.toFixed(2),
            sarChangePercent: sarChangePercent.toFixed(2) + '%'
          }
        });
      }
      
      // === 见顶信号检测（做空） - 进一步放宽条件 ===
      // 满足以下任意组合即可：
      // 1. 长上影线 + RSI超买(>60)
      // 2. 长上影线 + SAR加速向下
      // 3. RSI极度超买(>75) + 震荡>1%
      const sellCondition1 = hasLongUpperShadow && rsi5min > 60;
      const sellCondition2 = hasLongUpperShadow && sarChangePercent < 0 && Math.abs(sarChangePercent) > 3;
      const sellCondition3 = rsi5min > 75 && volatility > 1;
      
      if (
        (sellCondition1 || sellCondition2 || sellCondition3) &&
        (volumeAboveV1 || volumeAboveV2 || significantChange || volatility > 1)
      ) {
        signals.push({
          symbol: current.symbol,
          time: current.time,
          type: 'SELL', // 做空信号
          price: currentHigh, // 以最高价作为做空价格
          reason: '见顶信号',
          details: {
            volatility: volatility.toFixed(2) + '%',
            upperShadowRatio: (upperShadow / bodySize).toFixed(2) + 'x',
            volumeDecay: ((currentVolume / prevVolume) * 100).toFixed(1) + '%',
            sarChangePercent: sarChangePercent.toFixed(2) + '%',
            changePercent: changePercent.toFixed(2) + '%',
            rsi5min: rsi5min.toFixed(2),
            currentVolume: currentVolume.toFixed(2),
            volumeLevel: volumeAboveV1 ? 'V1+' : volumeAboveV2 ? 'V2+' : 'Normal'
          },
          strength: this.calculateSignalStrength({
            volatility,
            rsi: rsi5min,
            sarChange: Math.abs(sarChangePercent),
            volumeRatio: currentVolume / avgVolume,
            isTop: true
          }),
          keepBars: 10 // 保留10根K线
        });
      }
      
      // === 见底信号检测（做多） - 进一步放宽条件 ===
      // 满足以下任意组合即可：
      // 1. 长下影线 + RSI超卖(<40)
      // 2. 长下影线 + SAR加速向上
      // 3. RSI极度超卖(<25) + 震荡>1%
      const buyCondition1 = hasLongLowerShadow && rsi5min < 40;
      const buyCondition2 = hasLongLowerShadow && sarChangePercent > 0 && Math.abs(sarChangePercent) > 3;
      const buyCondition3 = rsi5min < 25 && volatility > 1;
      
      if (
        (buyCondition1 || buyCondition2 || buyCondition3) &&
        (volumeAboveV1 || volumeAboveV2 || significantChange || volatility > 1)
      ) {
        signals.push({
          symbol: current.symbol,
          time: current.time,
          type: 'BUY', // 做多信号
          price: currentLow, // 以最低价作为做多价格
          reason: '见底信号',
          details: {
            volatility: volatility.toFixed(2) + '%',
            lowerShadowRatio: (lowerShadow / bodySize).toFixed(2) + 'x',
            volumeDecay: ((currentVolume / prevVolume) * 100).toFixed(1) + '%',
            sarChangePercent: sarChangePercent.toFixed(2) + '%',
            changePercent: changePercent.toFixed(2) + '%',
            rsi5min: rsi5min.toFixed(2),
            currentVolume: currentVolume.toFixed(2),
            volumeLevel: volumeAboveV1 ? 'V1+' : volumeAboveV2 ? 'V2+' : 'Normal'
          },
          strength: this.calculateSignalStrength({
            volatility,
            rsi: rsi5min,
            sarChange: Math.abs(sarChangePercent),
            volumeRatio: currentVolume / avgVolume,
            isTop: false
          }),
          keepBars: 20 // 保留20根K线
        });
      }
      
      // === 波段高点信号检测（卖出） ===
      // 条件：
      // 1. RSI 5分钟 > 65（超买区域）
      // 2. 涨跌幅 ≤ 0.1%（横盘整理，价格不再上涨）
      // 3. 成交量 >= V2（有一定成交量支撑）
      const isPeakRSI = rsi5min > 65;
      const isSmallChange = Math.abs(changePercent) <= 0.1;
      const hasVolume = volumeAboveV2 || volumeAboveV1;
      
      if (isPeakRSI && isSmallChange && hasVolume) {
        signals.push({
          symbol: current.symbol,
          time: current.time,
          type: 'SELL', // 卖出信号
          price: currentClose, // 以收盘价作为卖出价格
          reason: '波段高点',
          details: {
            rsi5min: rsi5min.toFixed(2),
            changePercent: changePercent.toFixed(2) + '%',
            volatility: volatility.toFixed(2) + '%',
            sarChangePercent: sarChangePercent.toFixed(2) + '%',
            currentVolume: currentVolume.toFixed(2),
            volumeLevel: volumeAboveV1 ? 'V1+' : volumeAboveV2 ? 'V2+' : 'Normal',
            signal: current.signal || ''
          },
          strength: this.calculatePeakStrength({
            rsi: rsi5min,
            changePercent: Math.abs(changePercent),
            volumeRatio: currentVolume / avgVolume
          }),
          keepBars: 15 // 保留15根K线观察
        });
      }
      
      // 🆕 === 陷阱信号检测 ===
      // 计算当天涨幅：需要找到当天的第一根K线作为开盘价
      let todayGainPercent = 0;
      if (current.time) {
        // 获取当前K线的日期（格式：2025/10/27 17:25:00）
        const currentDate = current.time.split(' ')[0]; // "2025/10/27"
        
        // 从klineData中找到当天第一根K线（时间最早的）
        const todayKlines = klineData.filter(k => k.time && k.time.startsWith(currentDate));
        if (todayKlines.length > 0) {
          // 找到当天第一根K线（最早的时间）
          const firstKline = todayKlines.reduce((earliest, k) => {
            return k.time < earliest.time ? k : earliest;
          }, todayKlines[0]);
          
          const todayOpenPrice = parseFloat(firstKline.open);
          if (todayOpenPrice > 0) {
            todayGainPercent = ((currentClose - todayOpenPrice) / todayOpenPrice) * 100;
          }
        }
      }
      
      // 信号1: 急杀诱多（Long Exit / Short Entry）
      // 条件：涨跌幅 > -2%, V1=true, 当天涨幅 3%-10%
      if (changePercent > -2 && volumeAboveV1 && todayGainPercent > 3 && todayGainPercent < 10) {
        // Long Exit - 做多卖点
        signals.push({
          symbol: current.symbol,
          time: current.time,
          type: 'SELL',
          price: currentClose,
          reason: '急杀诱多',
          details: {
            changePercent: changePercent.toFixed(2) + '%',
            todayGainPercent: todayGainPercent.toFixed(2) + '%',
            currentVolume: currentVolume.toFixed(2),
            volumeLevel: 'V1+',
            rsi5min: rsi5min.toFixed(2),
            signal: current.signal || ''
          },
          strength: this.calculateTrapSignalStrength(changePercent, todayGainPercent, volumeAboveV1),
          keepBars: 15,
          category: 'trap_signal',
          signalClass: 'long_exit'
        });
        
        // Short Entry - 做空买点
        signals.push({
          symbol: current.symbol,
          time: current.time,
          type: 'SHORT_ENTRY',
          price: currentClose,
          reason: '急杀诱多',
          details: {
            changePercent: changePercent.toFixed(2) + '%',
            todayGainPercent: todayGainPercent.toFixed(2) + '%',
            currentVolume: currentVolume.toFixed(2),
            volumeLevel: 'V1+',
            rsi5min: rsi5min.toFixed(2),
            signal: current.signal || ''
          },
          strength: this.calculateTrapSignalStrength(changePercent, todayGainPercent, volumeAboveV1),
          keepBars: 15,
          category: 'trap_signal',
          signalClass: 'short_entry'
        });
      }
      
      // 信号2: 空头陷阱（Long Entry / Short Exit）
      // 条件：涨跌幅 > -3%, V1=true, 当天涨幅 < 0%
      if (changePercent > -3 && volumeAboveV1 && todayGainPercent < 0) {
        // Long Entry - 做多买点
        signals.push({
          symbol: current.symbol,
          time: current.time,
          type: 'BUY',
          price: currentClose,
          reason: '空头陷阱',
          details: {
            changePercent: changePercent.toFixed(2) + '%',
            todayGainPercent: todayGainPercent.toFixed(2) + '%',
            currentVolume: currentVolume.toFixed(2),
            volumeLevel: 'V1+',
            rsi5min: rsi5min.toFixed(2),
            signal: current.signal || ''
          },
          strength: this.calculateTrapSignalStrength(changePercent, todayGainPercent, volumeAboveV1),
          keepBars: 20,
          category: 'trap_signal',
          signalClass: 'long_entry'
        });
        
        // Short Exit - 做空卖点
        signals.push({
          symbol: current.symbol,
          time: current.time,
          type: 'SHORT_EXIT',
          price: currentClose,
          reason: '空头陷阱',
          details: {
            changePercent: changePercent.toFixed(2) + '%',
            todayGainPercent: todayGainPercent.toFixed(2) + '%',
            currentVolume: currentVolume.toFixed(2),
            volumeLevel: 'V1+',
            rsi5min: rsi5min.toFixed(2),
            signal: current.signal || ''
          },
          strength: this.calculateTrapSignalStrength(changePercent, todayGainPercent, volumeAboveV1),
          keepBars: 20,
          category: 'trap_signal',
          signalClass: 'short_exit'
        });
      }
    }

    // 🆕 === 主升信号检测 ===
    // 条件：
    // 1. 币种等级 >= 2
    // 2. 下跌后在底部
    // 3. 连续出现2个"震荡收敛"信号
    if (coinLevel !== undefined && coinLevel >= 1 && coinLevel <= 2) {
      // 查找连续的震荡收敛信号
      const convergenceSignals: number[] = []; // 记录震荡收敛信号的索引
      
      for (let i = 0; i < klineData.length; i++) {
        const k = klineData[i];
        // 检查通道状态是否为"震荡收敛"（注意字段名是 channel_state）
        if (k.channel_state && k.channel_state.includes('震荡收敛')) {
          convergenceSignals.push(i);
        }
      }
      
      // 检查是否有连续的2个震荡收敛信号
      for (let i = 0; i < convergenceSignals.length - 1; i++) {
        const idx1 = convergenceSignals[i];
        const idx2 = convergenceSignals[i + 1];
        
        // 判断是否连续（间隔不超过3根K线）
        if (idx2 - idx1 <= 3) {
          const signal1 = klineData[idx1];
          const signal2 = klineData[idx2];
          
          // 检查是否在底部：通过价格位置判断
          // 计算最近20根K线的价格范围
          const recentStart = Math.max(0, idx2 - 20);
          const recentKlines = klineData.slice(recentStart, idx2 + 1);
          const recentPrices = recentKlines.map(k => parseFloat(k.close));
          const recentHigh = Math.max(...recentPrices);
          const recentLow = Math.min(...recentPrices);
          const priceRange = recentHigh - recentLow;
          
          // 当前价格在底部30%区域
          const currentPrice = parseFloat(signal2.close);
          const pricePosition = ((currentPrice - recentLow) / priceRange) * 100;
          const isInBottomArea = pricePosition <= 30;
          
          // 检查是否从高位下跌：最近的最高价 > 当前价格的20%
          const priceDropPercent = ((recentHigh - currentPrice) / recentHigh) * 100;
          const hasDroppedFromHigh = priceDropPercent >= 20;
          
          // 如果在底部区域且从高位下跌，生成主升信号
          if (isInBottomArea && hasDroppedFromHigh) {
            const currentVolume = parseFloat(signal2.volume || '0');
            const avgVolume = klineData.slice(0, idx2).reduce((sum, k) => sum + parseFloat(k.volume || '0'), 0) / idx2;
            
            signals.push({
              symbol: signal2.symbol,
              time: signal2.time,
              type: 'BUY', // 做多信号
              price: parseFloat(signal2.close),
              reason: '主升信号 🚀',
              details: {
                convergenceCount: '2次连续',
                coinLevel: `等级${coinLevel}`,
                pricePosition: pricePosition.toFixed(1) + '%（底部）',
                priceDropFromHigh: priceDropPercent.toFixed(1) + '%',
                signal1Time: signal1.time,
                signal2Time: signal2.time,
                channelState: signal2.channelState || '震荡收敛',
                currentVolume: currentVolume.toFixed(2),
                volumeRatio: (currentVolume / avgVolume).toFixed(2) + 'x'
              },
              strength: this.calculateMainRiseStrength({
                coinLevel,
                pricePosition,
                priceDropPercent,
                volumeRatio: currentVolume / avgVolume
              }),
              keepBars: 30 // 主升信号保留30根K线观察
            });
          }
        }
      }
    }

    // 统计信息
    const stats = {
      totalSignals: signals.length,
      buySignals: signals.filter(s => s.type === 'BUY').length,
      sellSignals: signals.filter(s => s.type === 'SELL').length,
      totalAlerts: alerts.length, // 新增：预警总数
      avgVolume: avgVolume.toFixed(2),
      v1Threshold: v1.toFixed(2),
      v2Threshold: v2.toFixed(2)
    };

    return { signals, alerts, stats };
  }

  // 计算信号强度（0-100）
  private calculateSignalStrength(params: {
    volatility: number;
    rsi: number;
    sarChange: number;
    volumeRatio: number;
    isTop: boolean;
  }): number {
    let strength = 0;

    // RSI极值加分（0-30分）
    if (params.isTop) {
      if (params.rsi > 80) strength += 30;
      else if (params.rsi > 75) strength += 20;
      else if (params.rsi > 70) strength += 10;
    } else {
      if (params.rsi < 20) strength += 30;
      else if (params.rsi < 25) strength += 20;
      else if (params.rsi < 30) strength += 10;
    }

    // SAR加速度加分（0-25分）
    if (params.sarChange > 20) strength += 25;
    else if (params.sarChange > 15) strength += 20;
    else if (params.sarChange > 10) strength += 15;
    else if (params.sarChange > 5) strength += 10;

    // 震荡幅度加分（0-20分）
    if (params.volatility > 3) strength += 20;
    else if (params.volatility > 2) strength += 15;
    else if (params.volatility > 1.5) strength += 10;
    else if (params.volatility > 1) strength += 5;

    // 成交量加分（0-25分）
    if (params.volumeRatio > 2) strength += 25;
    else if (params.volumeRatio > 1.5) strength += 20;
    else if (params.volumeRatio > 1.2) strength += 15;
    else if (params.volumeRatio > 1) strength += 10;

    return Math.min(100, strength);
  }

  // 🆕 计算主升信号强度
  private calculateMainRiseStrength(params: {
    coinLevel: number;      // 币种等级（1-6）
    pricePosition: number;  // 价格位置百分比（0-100，越小越靠近底部）
    priceDropPercent: number; // 从高位下跌的百分比
    volumeRatio: number;    // 成交量比率
  }): number {
    let strength = 0;

    // 币种等级加分（0-40分）
    // 等级越高（数字越小），加分越高
    if (params.coinLevel === 1) strength += 40;
    else if (params.coinLevel === 2) strength += 35;
    else if (params.coinLevel === 3) strength += 25;
    else if (params.coinLevel === 4) strength += 15;
    else if (params.coinLevel === 5) strength += 10;
    else if (params.coinLevel === 6) strength += 5;

    // 价格位置加分（0-30分）
    // 越靠近底部，加分越高
    if (params.pricePosition <= 10) strength += 30;
    else if (params.pricePosition <= 20) strength += 25;
    else if (params.pricePosition <= 30) strength += 20;
    else if (params.pricePosition <= 40) strength += 10;

    // 下跌幅度加分（0-20分）
    // 从高位下跌幅度越大，反弹潜力越大
    if (params.priceDropPercent >= 50) strength += 20;
    else if (params.priceDropPercent >= 40) strength += 18;
    else if (params.priceDropPercent >= 30) strength += 15;
    else if (params.priceDropPercent >= 20) strength += 10;

    // 成交量加分（0-10分）
    if (params.volumeRatio > 1.5) strength += 10;
    else if (params.volumeRatio > 1.2) strength += 8;
    else if (params.volumeRatio > 1) strength += 5;

    return Math.min(100, strength);
  }

  // 🆕 计算波段高点信号强度
  private calculatePeakStrength(params: {
    rsi: number;           // RSI值（越高越强）
    changePercent: number; // 涨跌幅绝对值（越小越好，表示横盘）
    volumeRatio: number;   // 成交量比率
  }): number {
    let strength = 0;

    // RSI超买加分（0-40分）
    // RSI越高，超买信号越强
    if (params.rsi > 75) strength += 40;
    else if (params.rsi > 70) strength += 35;
    else if (params.rsi > 68) strength += 30;
    else if (params.rsi > 65) strength += 25;

    // 横盘整理加分（0-35分）
    // 涨跌幅越小，横盘信号越明显
    if (params.changePercent <= 0.05) strength += 35;
    else if (params.changePercent <= 0.08) strength += 30;
    else if (params.changePercent <= 0.1) strength += 25;
    else if (params.changePercent <= 0.15) strength += 15;

    // 成交量加分（0-25分）
    if (params.volumeRatio > 1.5) strength += 25;
    else if (params.volumeRatio > 1.2) strength += 20;
    else if (params.volumeRatio > 1.0) strength += 15;
    else if (params.volumeRatio > 0.8) strength += 10;

    return Math.min(100, strength);
  }

  // 获取多个币种的买卖点信号
  async detectMultiSymbolSignals(
    symbols: string[],
    getKlineData: (symbol: string) => Promise<any>
  ): Promise<any> {
    const results: any = {};

    // 🆕 批量获取所有币种的优先级等级
    const priorityLevels = new Map<string, number>();
    if (this.db) {
      const prioritiesResult: any = await this.db
        .prepare('SELECT symbol, level FROM coin_priority')
        .all();
      
      if (prioritiesResult.results) {
        prioritiesResult.results.forEach((p: any) => {
          priorityLevels.set(p.symbol, p.level);
        });
      }
    }

    for (const symbol of symbols) {
      try {
        const klineData = await getKlineData(symbol);
        // 🆕 获取币种等级
        const coinLevel = priorityLevels.get(symbol);
        const detection = this.detectTradingSignals(klineData, coinLevel);
        
        // 🆕 检测支撑线买入信号
        const supportLineSignals = await this.detectSupportLineBuySignals(symbol, klineData, 10);
        
        // 合并信号
        const allSignals = [...(detection.signals || []), ...supportLineSignals];
        
        results[symbol] = {
          success: true,
          signals: allSignals,
          alerts: detection.alerts || [],
          stats: detection.stats
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

  // 生成买卖点摘要
  generateSignalSummary(allResults: any): any {
    const summary: any = {
      totalSymbols: 0,
      totalSignals: 0,
      totalBuySignals: 0,
      totalSellSignals: 0,
      topBuySignals: [],
      topSellSignals: [],
      symbolsWithSignals: []
    };

    for (const [symbol, result] of Object.entries(allResults)) {
      if ((result as any).success && (result as any).signals) {
        summary.totalSymbols++;
        const signals = (result as any).signals || [];
        const buySignals = signals.filter((s: any) => s.type === 'BUY');
        const sellSignals = signals.filter((s: any) => s.type === 'SELL');

        summary.totalSignals += signals.length;
        summary.totalBuySignals += buySignals.length;
        summary.totalSellSignals += sellSignals.length;

        if (signals.length > 0) {
          summary.symbolsWithSignals.push({
            symbol,
            buyCount: buySignals.length,
            sellCount: sellSignals.length
          });

          // 收集高强度信号
          buySignals.forEach((s: any) => {
            if (s.strength >= 60) {
              summary.topBuySignals.push({ symbol, ...s });
            }
          });

          sellSignals.forEach((s: any) => {
            if (s.strength >= 60) {
              summary.topSellSignals.push({ symbol, ...s });
            }
          });
        }
      }
    }

    // 按强度排序
    summary.topBuySignals.sort((a: any, b: any) => b.strength - a.strength);
    summary.topSellSignals.sort((a: any, b: any) => b.strength - a.strength);

    // 只保留前10个
    summary.topBuySignals = summary.topBuySignals.slice(0, 10);
    summary.topSellSignals = summary.topSellSignals.slice(0, 10);

    return summary;
  }

  // 保存买卖点信号到数据库
  async saveTradingSignal(signal: any): Promise<void> {
    if (!this.db) return;

    try {
      // 提取K线时间（signal.time格式：2025/10/28 16:10:00）
      const klineTime = this.extractKlineTime(signal.time);
      
      await this.db
        .prepare(`
          INSERT INTO trading_signals (
            symbol, signal_time, signal_type, price, reason, 
            strength, details, keep_bars, kline_time
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        `)
        .bind(
          signal.symbol,
          signal.time,
          signal.type,
          signal.price,
          signal.reason || '',
          signal.strength || 0,
          JSON.stringify(signal.details || {}),
          signal.keepBars || 0,
          klineTime
        )
        .run();
    } catch (error) {
      console.error('保存买卖点信号失败:', error);
    }
  }

  // 从信号时间中提取K线时间（5分钟K线的开始时间）
  private extractKlineTime(signalTime: string): string {
    // signalTime格式: "2025/10/28 16:10:00"
    // 需要将分钟数向下取整到5的倍数
    try {
      const parts = signalTime.split(' ');
      if (parts.length !== 2) return signalTime;
      
      const datePart = parts[0];
      const timePart = parts[1];
      const timeComponents = timePart.split(':');
      
      if (timeComponents.length !== 3) return signalTime;
      
      const hour = timeComponents[0];
      const minute = parseInt(timeComponents[1]);
      
      // 将分钟数向下取整到5的倍数
      const klineMinute = Math.floor(minute / 5) * 5;
      
      return `${datePart} ${hour}:${klineMinute.toString().padStart(2, '0')}:00`;
    } catch (error) {
      console.error('提取K线时间失败:', error);
      return signalTime;
    }
  }

  // 保存预警信号到数据库
  async saveAlertSignal(alert: any): Promise<void> {
    if (!this.db) return;

    try {
      const klineData = alert.klineData || {};
      
      await this.db
        .prepare(`
          INSERT INTO alert_signals (
            symbol, alert_time, kline_index, triggers,
            volume, volume_level, change_percent, volatility,
            rsi_5min, sar_change_percent,
            open_price, high_price, low_price, close_price,
            boll_upper, boll_middle, boll_lower,
            rsi_1h, sar_value, sar_direction
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `)
        .bind(
          alert.symbol,
          alert.time,
          alert.index || 0,
          JSON.stringify(alert.triggers || []),
          parseFloat(alert.data.volume || '0'),
          alert.data.volumeLevel || 'Normal',
          parseFloat(alert.data.changePercent || '0'),
          parseFloat(alert.data.volatility || '0'),
          parseFloat(alert.data.rsi5min || '50'),
          parseFloat(alert.data.sarChangePercent || '0'),
          // 新增K线数据
          klineData.open || 0,
          klineData.high || 0,
          klineData.low || 0,
          klineData.close || 0,
          klineData.boll_upper || 0,
          klineData.boll_middle || 0,
          klineData.boll_lower || 0,
          klineData.rsi_1h || 0,
          klineData.sar_value || 0,
          klineData.sar_direction || ''
        )
        .run();
    } catch (error) {
      console.error('保存预警信号失败:', error);
    }
  }

  // 批量保存信号
  async saveSignalsAndAlerts(signals: any[], alerts: any[]): Promise<void> {
    if (!this.db) return;

    // 保存买卖点信号
    for (const signal of signals) {
      await this.saveTradingSignal(signal);
    }

    // 保存预警
    for (const alert of alerts) {
      await this.saveAlertSignal(alert);
    }
  }

  // 获取最近的买卖点信号（使用北京时间）
  async getRecentTradingSignals(hours: number = 24, limit: number = 100): Promise<any[]> {
    if (!this.db) return [];

    try {
      // 🔥 只统计当天的信号（从北京时间今天0点开始）
      const todayStart = getBeijingTodayStart();
      
      const result = await this.db
        .prepare(`
          SELECT * FROM trading_signals 
          WHERE created_at >= ?
          ORDER BY created_at DESC
          LIMIT ?
        `)
        .bind(todayStart, limit)
        .all();

      return result.results.map((row: any) => ({
        ...row,
        details: JSON.parse(row.details || '{}')
      }));
    } catch (error) {
      console.error('获取买卖点信号失败:', error);
      return [];
    }
  }

  // 获取最近的预警信号
  async getRecentAlertSignals(hours: number = 24, limit: number = 1000): Promise<any[]> {
    if (!this.db) return [];

    try {
      // 🔥 只统计当天的信号（从北京时间今天0点开始）
      const todayStart = getBeijingTodayStart();
      
      const result = await this.db
        .prepare(`
          SELECT * FROM alert_signals 
          WHERE created_at >= ?
          ORDER BY alert_time DESC
          LIMIT ?
        `)
        .bind(todayStart, limit)
        .all();

      return result.results.map((row: any) => ({
        ...row,
        triggers: JSON.parse(row.triggers || '[]'),
        // K线完整数据
        klineData: {
          open: row.open_price || 0,
          high: row.high_price || 0,
          low: row.low_price || 0,
          close: row.close_price || 0,
          volume: row.volume || 0,
          boll_upper: row.boll_upper || 0,
          boll_middle: row.boll_middle || 0,
          boll_lower: row.boll_lower || 0,
          rsi_1h: row.rsi_1h || 0,
          rsi_5min: row.rsi_5min || 0,
          sar_value: row.sar_value || 0,
          sar_direction: row.sar_direction || ''
        },
        data: {
          volume: row.volume?.toString() || '0',
          volumeLevel: row.volume_level,
          changePercent: row.change_percent?.toFixed(2) + '%',
          volatility: row.volatility?.toFixed(2) + '%',
          rsi5min: row.rsi_5min?.toFixed(2),
          sarChangePercent: row.sar_change_percent?.toFixed(2) + '%'
        }
      }));
    } catch (error) {
      console.error('获取预警信号失败:', error);
      return [];
    }
  }

  // 🆕 获取未发送到Telegram的买卖点信号
  async getUnsentTradingSignals(symbol: string, hours: number = 2): Promise<any[]> {
    if (!this.db) return [];

    try {
      // 🔥 只查询当天的信号（从北京时间今天0点开始）
      const todayStart = getBeijingTodayStart();
      
      const result = await this.db
        .prepare(`
          SELECT * FROM trading_signals 
          WHERE symbol = ? 
            AND telegram_sent = 0
            AND created_at >= ?
          ORDER BY signal_time DESC
        `)
        .bind(symbol, todayStart)
        .all();

      return result.results.map((row: any) => ({
        ...row,
        details: JSON.parse(row.details || '{}')
      }));
    } catch (error) {
      console.error('获取未发送买卖点信号失败:', error);
      return [];
    }
  }

  // 🆕 获取未发送到Telegram的预警信号
  async getUnsentAlertSignals(symbol: string, hours: number = 2): Promise<any[]> {
    if (!this.db) return [];

    try {
      // 🔥 只查询当天的信号（从北京时间今天0点开始）
      const todayStart = getBeijingTodayStart();
      
      const result = await this.db
        .prepare(`
          SELECT * FROM alert_signals 
          WHERE symbol = ? 
            AND telegram_sent = 0
            AND created_at >= ?
          ORDER BY alert_time DESC
        `)
        .bind(symbol, todayStart)
        .all();

      return result.results.map((row: any) => ({
        ...row,
        triggers: JSON.parse(row.triggers || '[]'),
        klineData: {
          open: row.open_price || 0,
          high: row.high_price || 0,
          low: row.low_price || 0,
          close: row.close_price || 0,
          volume: row.volume || 0,
          boll_upper: row.boll_upper || 0,
          boll_middle: row.boll_middle || 0,
          boll_lower: row.boll_lower || 0,
          rsi_1h: row.rsi_1h || 0,
          rsi_5min: row.rsi_5min || 0,
          sar_value: row.sar_value || 0,
          sar_direction: row.sar_direction || ''
        },
        data: {
          volume: row.volume?.toString() || '0',
          volumeLevel: row.volume_level,
          changePercent: row.change_percent?.toFixed(2) + '%',
          volatility: row.volatility?.toFixed(2) + '%',
          rsi5min: row.rsi_5min?.toFixed(2),
          sarChangePercent: row.sar_change_percent?.toFixed(2) + '%'
        }
      }));
    } catch (error) {
      console.error('获取未发送预警信号失败:', error);
      return [];
    }
  }

  // 🆕 标记买卖点信号为已发送
  async markTradingSignalsAsSent(signalIds: number[]): Promise<void> {
    if (!this.db || signalIds.length === 0) return;

    try {
      const placeholders = signalIds.map(() => '?').join(',');
      await this.db
        .prepare(`
          UPDATE trading_signals 
          SET telegram_sent = 1 
          WHERE id IN (${placeholders})
        `)
        .bind(...signalIds)
        .run();
      
      console.log(`✅ 标记 ${signalIds.length} 个买卖点信号为已发送`);
    } catch (error) {
      console.error('标记买卖点信号失败:', error);
    }
  }

  // 🆕 标记预警信号为已发送
  async markAlertSignalsAsSent(alertIds: number[]): Promise<void> {
    if (!this.db || alertIds.length === 0) return;

    try {
      const placeholders = alertIds.map(() => '?').join(',');
      await this.db
        .prepare(`
          UPDATE alert_signals 
          SET telegram_sent = 1 
          WHERE id IN (${placeholders})
        `)
        .bind(...alertIds)
        .run();
      
      console.log(`✅ 标记 ${alertIds.length} 个预警信号为已发送`);
    } catch (error) {
      console.error('标记预警信号失败:', error);
    }
  }

  // 🆕 获取信号发送配置
  async getSignalSendConfig(): Promise<Map<string, boolean>> {
    if (!this.db) return new Map();

    try {
      const result = await this.db
        .prepare('SELECT signal_category, signal_type, enabled FROM signal_send_config')
        .all();

      const config = new Map<string, boolean>();
      result.results.forEach((row: any) => {
        const key = `${row.signal_category}:${row.signal_type}`;
        config.set(key, row.enabled === 1);
      });

      return config;
    } catch (error) {
      console.error('获取信号发送配置失败:', error);
      return new Map();
    }
  }

  // 🆕 判断信号时间是否在允许发送的时间范围内
  // 规则：只发送本小时和上个小时最后10分钟的信号
  isTimeInAllowedRange(signalTime: string): boolean {
    try {
      // signalTime格式: "2025/10/28 16:10:00"
      // 转换为北京时间Date对象
      const parts = signalTime.replace(/\//g, '-').split(' ');
      const datePart = parts[0];
      const timePart = parts[1];
      const signalDate = new Date(`${datePart}T${timePart}+08:00`); // 北京时间
      
      // 当前北京时间
      const now = new Date();
      const beijingOffset = 8 * 60 * 60 * 1000;
      const beijingNow = new Date(now.getTime() + beijingOffset);
      
      // 提取信号的小时和分钟
      const signalHour = signalDate.getUTCHours();
      const signalMinute = signalDate.getUTCMinutes();
      
      // 提取当前的小时和分钟
      const currentHour = beijingNow.getUTCHours();
      const currentMinute = beijingNow.getUTCMinutes();
      
      // 判断是否是本小时
      if (signalHour === currentHour) {
        return true;
      }
      
      // 判断是否是上个小时的最后10分钟（50-59分）
      const prevHour = currentHour === 0 ? 23 : currentHour - 1;
      if (signalHour === prevHour && signalMinute >= 50) {
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('判断时间范围失败:', error);
      return false; // 解析失败则不发送
    }
  }

  // 🆕 检查该5分钟K线区间是否已经发送过信号
  async hasSignalSentForKline(symbol: string, klineTime: string, signalCategory: string): Promise<boolean> {
    if (!this.db) return false;

    try {
      const result: any = await this.db
        .prepare(`
          SELECT COUNT(*) as count 
          FROM signal_send_log 
          WHERE symbol = ? AND kline_time = ? AND signal_category = ?
        `)
        .bind(symbol, klineTime, signalCategory)
        .first();

      return result.count > 0;
    } catch (error) {
      console.error('检查K线发送记录失败:', error);
      return false;
    }
  }

  // 🆕 记录信号发送日志
  async recordSignalSent(symbol: string, klineTime: string, signalCategory: string, signalId: number): Promise<void> {
    if (!this.db) return;

    try {
      await this.db
        .prepare(`
          INSERT OR REPLACE INTO signal_send_log (symbol, kline_time, signal_category, signal_id)
          VALUES (?, ?, ?, ?)
        `)
        .bind(symbol, klineTime, signalCategory, signalId)
        .run();
    } catch (error) {
      console.error('记录信号发送日志失败:', error);
    }
  }

  // 🆕 获取符合条件的可发送买卖点信号
  // 规则：
  // 1. 同一币种同一5分钟K线只发一个信号
  // 2. 只发本小时和上个小时最后10分钟的信号
  // 3. 遵守配置表的启用/禁用设置
  async getSignalsToSend(): Promise<any[]> {
    if (!this.db) return [];

    try {
      // 获取发送配置
      const config = await this.getSignalSendConfig();
      
      // 获取所有未发送的买卖点信号
      const todayStart = getBeijingTodayStart();
      const result = await this.db
        .prepare(`
          SELECT * FROM trading_signals 
          WHERE telegram_sent = 0
            AND created_at >= ?
          ORDER BY symbol, kline_time DESC, created_at DESC
        `)
        .bind(todayStart)
        .all();

      const signals: any[] = [];
      const processedKlines = new Set<string>(); // 用于去重：symbol:kline_time

      for (const row of result.results) {
        const signal: any = {
          ...row,
          details: JSON.parse(row.details || '{}')
        };

        // 检查配置是否启用
        const configKey = `trading:${signal.signal_type}`;
        if (!config.get(configKey)) {
          continue; // 跳过未启用的信号类型
        }

        // 检查时间范围
        if (!this.isTimeInAllowedRange(signal.signal_time)) {
          continue; // 跳过不在允许时间范围内的信号
        }

        // 检查是否已经为该K线发送过信号
        const klineKey = `${signal.symbol}:${signal.kline_time}`;
        if (processedKlines.has(klineKey)) {
          continue; // 跳过同一K线的重复信号
        }

        // 检查数据库中是否已有该K线的发送记录
        const hasSent = await this.hasSignalSentForKline(signal.symbol, signal.kline_time, 'trading');
        if (hasSent) {
          continue;
        }

        // 通过所有检查，添加到发送列表
        signals.push(signal);
        processedKlines.add(klineKey);
      }

      return signals;
    } catch (error) {
      console.error('获取待发送信号失败:', error);
      return [];
    }
  }

  /**
   * 检测支撑线买入信号
   * @param symbol 币种符号
   * @param klineData K线数据数组
   * @param displayLimitBars 显示限制：每N根K线最多显示1个信号 (默认10)
   * @returns 支撑线买入信号数组
   */
  async detectSupportLineBuySignals(symbol: string, klineData: any[], displayLimitBars: number = 10): Promise<any[]> {
    if (!this.db) {
      return [];
    }

    try {
      // 1. 获取今天的支撑线价格
      const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
      const supportLineResult = await this.db.prepare(`
        SELECT support_price 
        FROM support_lines 
        WHERE symbol = ? AND date = ?
        ORDER BY created_at DESC 
        LIMIT 1
      `).bind(symbol, today).first();

      if (!supportLineResult || !supportLineResult.support_price) {
        return []; // 该币种今天没有设置支撑线
      }

      const supportPrice = parseFloat(supportLineResult.support_price as string);
      const signals: any[] = [];
      let lastSignalIndex = -displayLimitBars; // 上一个信号的索引

      // 2. 遍历K线数据，检测是否接近支撑线（±0.5%）
      for (let i = 0; i < klineData.length; i++) {
        const k = klineData[i];
        const currentPrice = parseFloat(k.close);
        const priceDiff = Math.abs(currentPrice - supportPrice);
        const priceDiffPercent = (priceDiff / supportPrice) * 100;

        // 3. 检查是否在0.5%范围内
        if (priceDiffPercent <= 0.5) {
          // 4. 检查显示限制：与上一个信号间隔至少displayLimitBars根K线
          if (i - lastSignalIndex >= displayLimitBars) {
            signals.push({
              symbol: k.symbol,
              time: k.time,
              type: 'BUY', // 做多信号
              price: currentPrice,
              reason: '支撑买入',
              details: {
                supportPrice: supportPrice.toFixed(8),
                currentPrice: currentPrice.toFixed(8),
                distance: priceDiffPercent.toFixed(2) + '%',
                distanceDirection: currentPrice >= supportPrice ? '接近支撑线上方' : '接近支撑线下方',
                rsi5min: parseFloat(k.rsi_5min || '50').toFixed(2),
                changePercent: parseFloat(k.change?.replace('%', '') || '0').toFixed(2) + '%',
                volume: parseFloat(k.volume || '0').toFixed(2)
              },
              strength: this.calculateSupportLineSignalStrength(priceDiffPercent),
              keepBars: 20, // 保留20根K线观察
              category: 'support_line'
            });
            lastSignalIndex = i; // 更新上一个信号索引
          }
        }
      }

      return signals;
    } catch (error) {
      console.error(`检测${symbol}支撑线买入信号失败:`, error);
      return [];
    }
  }

  /**
   * 计算支撑线信号强度
   * @param distancePercent 价格与支撑线的距离百分比
   * @returns 信号强度 (0-100)
   */
  private calculateSupportLineSignalStrength(distancePercent: number): number {
    // 距离越近，信号强度越高
    // 0% -> 100, 0.5% -> 50
    const strength = Math.max(0, 100 - (distancePercent / 0.5) * 50);
    return Math.round(strength);
  }

  /**
   * 计算陷阱信号强度
   * @param changePercent 当前K线涨跌幅
   * @param todayGainPercent 当天涨幅
   * @param hasV1Volume 是否有V1成交量
   * @returns 信号强度 (0-100)
   */
  private calculateTrapSignalStrength(changePercent: number, todayGainPercent: number, hasV1Volume: boolean): number {
    let strength = 50; // 基础强度
    
    // V1成交量加分
    if (hasV1Volume) {
      strength += 20;
    }
    
    // 根据当前涨跌幅调整（越接近0越强）
    const changeScore = Math.max(0, 15 - Math.abs(changePercent) * 5);
    strength += changeScore;
    
    // 根据当天涨幅位置调整
    if (todayGainPercent > 3 && todayGainPercent < 10) {
      // 急杀诱多：在3%-10%范围内，越接近中间越强
      const optimal = 6.5; // 最优点
      const distance = Math.abs(todayGainPercent - optimal);
      const gainScore = Math.max(0, 15 - distance * 2);
      strength += gainScore;
    } else if (todayGainPercent < 0) {
      // 空头陷阱：跌幅越大越强（但不超过-5%）
      const absGain = Math.abs(todayGainPercent);
      const gainScore = Math.min(15, absGain * 3);
      strength += gainScore;
    }
    
    return Math.min(100, Math.round(strength));
  }
}

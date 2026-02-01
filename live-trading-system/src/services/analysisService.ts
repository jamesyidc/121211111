import { CoinService, coingeckoIdToSymbol } from './coinService';
import { TelegramService } from './telegramService';
import type { MarketTrend, StarType, CoinLevel } from '../types';
import { getBeijingISOString, getBeijingDateString, convertUTCtoBeijingDateString } from '../utils/timeUtils';

export class AnalysisService {
  private coinService: CoinService;
  private telegramService: TelegramService;

  constructor(coinService: CoinService) {
    this.coinService = coinService;
    this.telegramService = new TelegramService();
  }

  // 执行一轮分析（使用北京时间）
  async performRoundAnalysis() {
    const roundTime = getBeijingISOString(); // 🔥 使用北京时间
    const today = getBeijingDateString(); // 🔥 使用北京时间日期

    try {
      // 🆕 0. 检查是否需要重置每日数据（隔天第一次刷新）
      const shouldReset = await this.coinService.shouldResetDailyExtremes();
      if (shouldReset) {
        await this.coinService.resetAllDailyData();
      }
      
      // 1. 获取最新价格数据 (带重试机制)
      let priceData = await this.coinService.fetchPricesFromCoinGecko();
      
      // 验证数据完整性 - 确保change_24h有值
      let hasValidChanges = Object.values(priceData).every((data: any) => 
        data.usd_24h_change !== undefined && data.usd_24h_change !== null
      );
      
      // 如果数据不完整,最多重试2次
      let retryCount = 0;
      while (!hasValidChanges && retryCount < 2) {
        console.log(`数据不完整,重试第 ${retryCount + 1} 次...`);
        await new Promise(resolve => setTimeout(resolve, 2000)); // 等待2秒
        priceData = await this.coinService.fetchPricesFromCoinGecko();
        hasValidChanges = Object.values(priceData).every((data: any) => 
          data.usd_24h_change !== undefined && data.usd_24h_change !== null
        );
        retryCount++;
      }
      
      if (!hasValidChanges) {
        console.warn('⚠️  警告: 部分币种的24小时涨跌幅数据缺失');
      }
      
      // 🆕 2. 检查价格是否有变化（防止保存无变化的数据）
      let priceChangedCount = 0;
      let hasAnyPreviousData = false;
      const sampleCheckSymbols = ['BTC', 'ETH', 'BNB']; // 检查主流币种
      
      for (const symbol of sampleCheckSymbols) {
        const coinGeckoId = Object.keys(priceData).find(id => 
          coingeckoIdToSymbol(id) === symbol
        );
        if (!coinGeckoId) continue;
        
        const data = priceData[coinGeckoId];
        const prevRecord = await this.coinService.getPreviousPriceRecord(symbol);
        
        if (prevRecord) {
          hasAnyPreviousData = true;
          if (Math.abs(data.usd - prevRecord.price) > 0.000001) {
            priceChangedCount++;
          }
        } else {
          // 首次运行，没有历史数据，接受新数据
          priceChangedCount++;
        }
      }
      
      // 🚫 如果主流币种价格都没变化，拒绝本次分析（仅当有历史数据时）
      if (hasAnyPreviousData && priceChangedCount === 0) {
        console.warn('⚠️ 价格数据未变化，跳过本次分析');
        throw new Error('价格数据未更新，请稍后再试（CoinGecko API可能返回了缓存数据）');
      }
      
      console.log(`✅ 价格变化检查通过: ${priceChangedCount}/${sampleCheckSymbols.length} 个币种有变化`);
      
      // 3. 分析每个币种
      const coinDetails: any[] = [];
      let greenCount = 0;
      let redCount = 0;
      let extremeUpCount = 0;
      let extremeDownCount = 0;
      let surgeCount = 0;
      let crashCount = 0;

      for (const [coinGeckoId, data] of Object.entries(priceData)) {
        const symbol = coingeckoIdToSymbol(coinGeckoId);
        if (!symbol) continue;

        // 🔧 先获取上一次价格（在保存当前价格之前）
        const prevRecord: any = await this.coinService.getPreviousPriceRecord(symbol);

        // 保存价格记录
        await this.coinService.savePriceRecord(symbol, data);
        
        let changePercent = 0;
        let changeAmount = 0;
        
        if (prevRecord) {
          changeAmount = data.usd - prevRecord.price;
          changePercent = (changeAmount / prevRecord.price) * 100;
        }

        // 判断涨跌（相对上一轮）
        const isGreen = changePercent > 0;
        const isRed = changePercent < 0;
        
        if (isGreen) greenCount++;
        if (isRed) redCount++;

        // 判断极端行情（相对上一轮）
        const isExtremeUp = changePercent >= 4;
        const isExtremeDown = changePercent <= -3;
        
        if (isExtremeUp) extremeUpCount++;
        if (isExtremeDown) extremeDownCount++;

        // 判断急涨急跌（相对上一轮）
        const isSurge = changePercent >= 1;
        const isCrash = changePercent <= -1;
        
        if (isSurge) surgeCount++;
        if (isCrash) crashCount++;

        // 检查创新高/新低，并实现动态计次系统
        const extreme: any = await this.coinService.getOrCreatePriceExtreme(symbol, data.usd);
        let newHighCount = 0;
        let newLowCount = 0;

        // 检查是否创新高
        if (data.usd > extreme.all_time_high) {
          // 创新高：更新极值并重置计次为0
          await this.coinService.updatePriceExtreme(symbol, 'high', data.usd);
          await this.coinService.saveExtremeRecord(symbol, 'new_high', data.usd, extreme.all_time_high, 0);
          newHighCount = 1;
          
          // 🔔 Telegram通知已禁用（避免错误）
          console.log(`🚀 创新高预警: ${symbol} - $${data.usd.toFixed(6)}`);
        } else {
          // 未创新高：计次加1
          await this.coinService.incrementExtremeCount(symbol, 'high');
        }

        // 检查是否创新低
        if (data.usd < extreme.all_time_low) {
          // 创新低：更新极值并重置计次为0
          await this.coinService.updatePriceExtreme(symbol, 'low', data.usd);
          await this.coinService.saveExtremeRecord(symbol, 'new_low', data.usd, extreme.all_time_low, 0);
          newLowCount = 1;
          
          // 🔔 Telegram通知已禁用（避免错误）
          console.log(`📉 创新低预警: ${symbol} - $${data.usd.toFixed(6)}`);
        } else {
          // 未创新低：计次加1
          await this.coinService.incrementExtremeCount(symbol, 'low');
        }

        // 极端行情累计次数管理（涨幅≥4% 或 跌幅≤-3%）
        if (isExtremeUp) {
          // 触发极端上涨：累加次数
          await this.coinService.incrementExtremeUpCount(symbol);
        } else {
          // 未触发极端上涨：重置计数（因为没有连续极端上涨）
          if (extreme.extreme_up_count > 0) {
            await this.coinService.resetExtremeUpCount(symbol);
          }
        }

        if (isExtremeDown) {
          // 触发极端下跌：累加次数
          await this.coinService.incrementExtremeDownCount(symbol);
        } else {
          // 未触发极端下跌：重置计数（因为没有连续极端下跌）
          if (extreme.extreme_down_count > 0) {
            await this.coinService.resetExtremeDownCount(symbol);
          }
        }

        coinDetails.push({
          symbol,
          price: data.usd,
          prev_price: prevRecord?.price || null,
          change_amount: changeAmount,
          change_percent: changePercent,
          is_green: isGreen,
          is_extreme_up: isExtremeUp,
          is_extreme_down: isExtremeDown,
          is_surge: isSurge,
          is_crash: isCrash,
          change_24h: data.usd_24h_change || 0,
          new_high_count: newHighCount,
          new_low_count: newLowCount
        });
      }

      // 4. 计算绿色占比
      const totalCoins = coinDetails.length;
      const greenRatio = totalCoins > 0 ? (greenCount / totalCoins) * 100 : 0;

      // 5. 风险提示（累计模式：当天累加，0:00清零，两次间隔≥10分钟）
      let riskAlertCount = 0;
      if (greenRatio === 0) {
        // 🆕 检查距离上次风险事件是否≥10分钟
        const lastEventTime = await this.coinService.getLastRiskEventTime(today);
        let shouldIncrement = true;
        
        if (lastEventTime) {
          const lastTime = new Date(lastEventTime).getTime();
          const currentTime = new Date().getTime();
          const minutesSinceLastEvent = (currentTime - lastTime) / (60 * 1000);
          
          if (minutesSinceLastEvent < 10) {
            console.log(`⏱️  距离上次风险事件仅${minutesSinceLastEvent.toFixed(1)}分钟，不累加`);
            shouldIncrement = false;
          } else {
            console.log(`✅ 距离上次风险事件${minutesSinceLastEvent.toFixed(1)}分钟，累加风险次数`);
          }
        }
        
        // 获取今天已有的风险提示次数
        const todayRiskCount = await this.coinService.getTodayRiskAlertCount(today);
        
        if (shouldIncrement) {
          riskAlertCount = todayRiskCount + 1;
          // 🆕 保存风险事件详情
          const eventTime = await this.coinService.saveRiskAlertEvent(
            roundTime, 
            greenRatio, 
            coinDetails.length
          );
          // 保存累计次数和最后事件时间
          await this.coinService.saveTodayRiskAlertCount(today, riskAlertCount, eventTime);
        } else {
          riskAlertCount = todayRiskCount;
        }
      } else {
        // 绿色占比不为0时，读取今天已有的累计次数（不增加）
        riskAlertCount = await this.coinService.getTodayRiskAlertCount(today);
      }

      // 6. 按24小时涨跌幅排名
      coinDetails.sort((a, b) => b.change_24h - a.change_24h);
      coinDetails.forEach((detail, index) => {
        detail.rank_in_round = index + 1;
      });

      // 7. 保存轮次统计
      await this.coinService.saveRoundStat(roundTime, {
        green_count: greenCount,
        red_count: redCount,
        green_ratio: greenRatio,
        extreme_up_count: extremeUpCount,
        extreme_down_count: extremeDownCount,
        surge_count: surgeCount,
        crash_count: crashCount,
        risk_alert_count: riskAlertCount
      });

      // 8. 计算相对上一轮的涨跌幅并保存单币详情
      const extendedCoinDetails = [];
      for (const detail of coinDetails) {
        // 获取上一轮的数据用于计算涨跌幅
        const previousRoundDetail: any = await this.coinService.getPreviousRoundDetail(detail.symbol);
        
        let changeVsPrevRound = 0;
        let isSurgeVsPrev = false;
        let isCrashVsPrev = false;
        let previousRoundTime = null;
        
        if (previousRoundDetail) {
          previousRoundTime = previousRoundDetail.round_time;
          changeVsPrevRound = ((detail.price - previousRoundDetail.price) / previousRoundDetail.price) * 100;
          isSurgeVsPrev = changeVsPrevRound >= 1;
          isCrashVsPrev = changeVsPrevRound <= -1;
        }
        
        // 添加轮次对比数据
        const extendedDetail = {
          ...detail,
          previous_round_time: previousRoundTime,
          change_vs_prev_round: changeVsPrevRound,
          is_surge_vs_prev: isSurgeVsPrev ? 1 : 0,
          is_crash_vs_prev: isCrashVsPrev ? 1 : 0
        };
        
        extendedCoinDetails.push(extendedDetail);
        await this.coinService.saveCoinRoundDetail(detail.symbol, roundTime, extendedDetail);
      }

      // 9. 更新日统计（使用轮次对比的急涨急跌数据）
      await this.updateDailyStats(today, extendedCoinDetails, surgeCount, crashCount);

      // 10. 更新币种优先级
      await this.updateCoinPriorities(extendedCoinDetails);

      return {
        success: true,
        roundTime,
        greenCount,
        redCount,
        greenRatio,
        extremeUpCount,
        extremeDownCount,
        surgeCount,
        crashCount,
        riskAlertCount
      };
    } catch (error: any) {
      console.error('Analysis error:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  // 更新日统计
  private async updateDailyStats(date: string, coinDetails: any[], roundSurges: number, roundCrashes: number) {
    for (const detail of coinDetails) {
      const existing: any = await this.coinService.getTodayStats(date);
      const coinStat = existing.find((s: any) => s.symbol === detail.symbol);

      // 使用相对上一轮的急涨急跌判断（is_surge_vs_prev, is_crash_vs_prev）
      const totalSurges = (coinStat?.total_surges || 0) + (detail.is_surge_vs_prev ? 1 : 0);
      const totalCrashes = (coinStat?.total_crashes || 0) + (detail.is_crash_vs_prev ? 1 : 0);
      const newHighCount = (coinStat?.new_high_count || 0) + detail.new_high_count;
      const newLowCount = (coinStat?.new_low_count || 0) + detail.new_low_count;

      // 计算市场趋势
      const { trend, strength, starRating, starType } = this.calculateMarketTrend(
        totalSurges,
        totalCrashes,
        newHighCount,
        newLowCount
      );

      await this.coinService.updateDailyStat(date, detail.symbol, {
        total_surges: totalSurges,
        total_crashes: totalCrashes,
        new_high_count: newHighCount,
        new_low_count: newLowCount,
        market_trend: trend,
        trend_strength: strength,
        star_rating: starRating,
        star_type: starType
      });
    }
  }

  // 计算市场趋势（新规则）
  private calculateMarketTrend(surges: number, crashes: number, newHighs: number, newLows: number) {
    let trend: MarketTrend = '无序震荡';
    let strength = 0;
    let starRating = 0;
    let starType: StarType | null = null;

    const highLowDiff = newHighs - newLows;

    // 新规则：只有急涨或急跌 >= 10 才计算比值和星级
    if (surges >= 10) {
      // 急涨主导
      const diff = surges - crashes;
      
      // 比值 = 差值 ÷ 急跌（如果急跌为0，则比值 = 差值）
      strength = crashes > 0 ? diff / crashes : diff;

      // 市场趋势判断
      if (highLowDiff >= 3) {
        trend = '单边主升';
      } else if (highLowDiff >= 1) {
        trend = '震荡偏多';
      }

      // 星级评定（实心黑星★）
      starType = '急涨';
      if (strength >= 1 && strength < 2) {
        starRating = 1;  // ★ 一颗实心黑星
      } else if (strength >= 2 && strength < 3) {
        starRating = 2;  // ★★ 二颗实心黑星
      } else if (strength >= 3) {
        starRating = 3;  // ★★★ 三颗实心黑星
      }

    } else if (crashes >= 10) {
      // 急跌主导
      const diff = crashes - surges;
      
      // 比值 = 差值 ÷ 急涨（如果急涨为0，则比值 = 差值）
      strength = surges > 0 ? diff / surges : diff;

      // 市场趋势判断
      const lowHighDiff = newLows - newHighs;
      if (lowHighDiff >= 3) {
        trend = '单边主跌';
      } else if (lowHighDiff >= 1) {
        trend = '震荡偏空';
      }

      // 星级评定（空心黑星☆）
      starType = '急跌';
      if (strength >= 1 && strength < 2) {
        starRating = 1;  // ☆ 一颗空心黑星
      } else if (strength >= 2 && strength < 3) {
        starRating = 2;  // ☆☆ 二颗空心黑星
      } else if (strength >= 3) {
        starRating = 3;  // ☆☆☆ 三颗空心黑星
      }
    }
    // 如果急涨和急跌都 < 10，则不计算比值和星级（保持默认值）

    return { trend, strength, starRating, starType };
  }

  // 更新币种优先级
  private async updateCoinPriorities(coinDetails: any[]) {
    const extremes: any = await this.coinService.getAllPriceExtremes();
    
    for (const detail of coinDetails) {
      const extreme = extremes.find((e: any) => e.symbol === detail.symbol);
      if (!extreme) continue;

      const lowRatio = (detail.price / extreme.all_time_low) * 100;
      const highRatio = (detail.price / extreme.all_time_high) * 100;

      const level = this.calculateCoinLevel(lowRatio, highRatio);

      await this.coinService.updateCoinPriority(detail.symbol, level, lowRatio, highRatio);
    }
  }

  // 计算币种等级
  private calculateCoinLevel(lowRatio: number, highRatio: number): CoinLevel {
    // 🔥 优化优先级算法：更精细的等级划分，考虑市场实际情况
    // highRatio = 当前价格/历史最高价 * 100，表示距离ATH的距离
    // lowRatio = 当前价格/历史最低价 * 100，表示距离ATL的距离
    
    // Level 1: 极端高位 - 接近历史最高且远离历史最低
    if (lowRatio >= 150 && highRatio >= 85) return 1;
    
    // Level 2: 高位 - 价格处于较高水平
    if ((lowRatio >= 130 && highRatio >= 70) || (lowRatio >= 120 && highRatio >= 80)) return 2;
    
    // Level 3: 中高位 - 价格相对较高
    if ((lowRatio >= 110 && highRatio >= 60) || (lowRatio >= 150 && highRatio >= 50)) return 3;
    
    // Level 4: 中等位置 - 价格在合理范围
    if ((lowRatio >= 105 && highRatio >= 40) || (lowRatio >= 120 && highRatio >= 30)) return 4;
    
    // Level 5: 中低位 - 价格相对较低，可能有机会
    if (lowRatio >= 105 || highRatio >= 25) return 5;
    
    // Level 6: 极端低位 - 非常接近历史最低
    return 6;
  }

  // 获取仪表板数据
  async getDashboardData() {
    // 获取最新轮次统计
    const latestRounds: any = await this.coinService.getLatestRoundStats(1);
    const latestRound = latestRounds[0];

    // 获取最新币种详情
    const coinDetails = latestRound 
      ? await this.coinService.getLatestCoinDetails(latestRound.round_time)
      : [];

    // 获取今日统计（使用北京时间日期）
    const today = getBeijingDateString(); // 🔥 使用北京时间日期
    let todayStats = await this.coinService.getTodayStats(today);
    
    // 🔧 如果今天没有数据，尝试获取最近一天的数据
    if (!todayStats || todayStats.length === 0) {
      const recentStatsResult = await this.coinService.db
        .prepare('SELECT DISTINCT date FROM daily_stats ORDER BY date DESC LIMIT 1')
        .first();
      
      if (recentStatsResult) {
        const recentDate = (recentStatsResult as any).date;
        todayStats = await this.coinService.getTodayStats(recentDate);
        console.log(`📊 今日(${today})无数据，使用最近日期(${recentDate})的统计数据`);
      }
    }

    // 获取极值数据
    const extremes = await this.coinService.getAllPriceExtremes();

    // 获取优先级基础数据
    const priorities = await this.coinService.getAllCoinPriorities();
    
    // 🆕 动态计算每个币种的优先级等级（基于实时占比）
    // 等级规则：
    // 等级1: 最高占比>90 且 最低占比>120
    // 等级2: 最高占比>80 且 最低占比>120
    // 等级3: 最高占比>90 且 最低占比>110
    // 等级4: 最高占比>70 且 最低占比>120
    // 等级5: 最高占比>80 且 最低占比>110
    // 等级6: 其他情况（最高占比<80 或 最低占比<110）
    const calculatePriorityLevel = (highRatio: number, lowRatio: number): number => {
      if (highRatio > 90 && lowRatio > 120) return 1;
      if (highRatio > 80 && lowRatio > 120) return 2;
      if (highRatio > 90 && lowRatio > 110) return 3;
      if (highRatio > 70 && lowRatio > 120) return 4;
      if (highRatio > 80 && lowRatio > 110) return 5;
      return 6; // 最高占比<80 或 最低占比<110
    };
    
    // 为每个币种计算实时占比并更新优先级等级
    const enhancedPriorities = priorities.map((priority: any) => {
      const extreme = extremes.find((ext: any) => ext.symbol === priority.symbol);
      const coinDetail = coinDetails.find((coin: any) => coin.symbol === priority.symbol);
      
      let highRatio = priority.high_ratio || 0;
      let lowRatio = priority.low_ratio || 0;
      
      // 如果有实时价格和极值数据，计算实时占比
      if (extreme && coinDetail && coinDetail.price) {
        highRatio = extreme.all_time_high > 0 
          ? (coinDetail.price / extreme.all_time_high) * 100 
          : 0;
        lowRatio = extreme.all_time_low > 0 
          ? (coinDetail.price / extreme.all_time_low) * 100 
          : 0;
      }
      
      // 根据实时占比计算优先级等级
      const level = calculatePriorityLevel(highRatio, lowRatio);
      
      return {
        ...priority,
        level: level, // 动态计算的等级
        high_ratio: highRatio, // 实时最高占比
        low_ratio: lowRatio // 实时最低占比
      };
    });
    
    // 增强coinDetails数据：添加当天急涨急跌累计次数和极端行情累计次数
    const enhancedCoinDetails = coinDetails.map((detail: any) => {
      const todayStat = todayStats.find((stat: any) => stat.symbol === detail.symbol);
      const extreme = extremes.find((ext: any) => ext.symbol === detail.symbol);
      return {
        ...detail,
        // 当天急涨急跌累计次数
        today_surge_count: todayStat?.total_surges || 0,
        today_crash_count: todayStat?.total_crashes || 0,
        // 极端行情累计次数（+4% 和 -3%）
        extreme_up_count: extreme?.extreme_up_count || 0,
        extreme_down_count: extreme?.extreme_down_count || 0
      };
    });

    // 🆕 计算24小时涨跌幅超过10%的统计
    const totalCoins = enhancedCoinDetails.length;
    const change24hOver10Up = enhancedCoinDetails.filter((coin: any) => coin.change_24h >= 10).length;
    const change24hOver10Down = enhancedCoinDetails.filter((coin: any) => coin.change_24h <= -10).length;
    const change24hOver10UpPercent = totalCoins > 0 ? ((change24hOver10Up / totalCoins) * 100).toFixed(1) : '0.0';
    const change24hOver10DownPercent = totalCoins > 0 ? ((change24hOver10Down / totalCoins) * 100).toFixed(1) : '0.0';

    // 🆕 查询今日创新高/新低的总次数
    const todayNewHighCount = await this.coinService.getTodayExtremeCount(today, 'high');
    const todayNewLowCount = await this.coinService.getTodayExtremeCount(today, 'low');

    // 🆕 查询今日每个币种的V1触发次数
    const todayV1Counts = await this.coinService.getTodayV1Counts(today);

    // 🆕 计算当天涨幅（使用OKX永续合约1天K线涨跌幅）
    const todayChanges = await this.coinService.getOKXDailyChanges();
    
    // 🆕 获取每个币种的最新K线时间（OKX数据）
    const klineLatestTimes: Record<string, number> = {};
    const klineTimesResult = await this.coinService.db
      .prepare('SELECT symbol, MAX(open_time) as latest_time FROM kline_data GROUP BY symbol')
      .all();
    
    (klineTimesResult.results as any[]).forEach((row: any) => {
      klineLatestTimes[row.symbol] = row.latest_time;
    });
    
    // 🆕 增强coinDetails数据：添加今日V1触发次数、当天涨幅和K线最新时间
    const finalEnhancedCoinDetails = enhancedCoinDetails.map((detail: any) => {
      // 使用OKX永续合约1天K线的涨跌幅作为当天涨幅
      const change_today = todayChanges[detail.symbol] || null;
      
      // 使用K线数据的最新时间（毫秒时间戳转为ISO字符串）
      const kline_latest_time = klineLatestTimes[detail.symbol] 
        ? new Date(klineLatestTimes[detail.symbol]).toISOString()
        : null;
      
      return {
        ...detail,
        today_v1_count: todayV1Counts[detail.symbol] || 0,
        change_today: change_today, // 当天涨幅（%）- 基于OKX永续合约1天K线涨跌幅
        kline_latest_time: kline_latest_time // K线最新时间（OKX数据）
      };
    });

    // 🆕 计算平均涨跌幅（从coin_round_details计算）
    let averageChange = 0;
    if (latestRound && finalEnhancedCoinDetails.length > 0) {
      const totalChange = finalEnhancedCoinDetails.reduce((sum: number, coin: any) => 
        sum + (coin.change_percent || 0), 0);
      averageChange = totalChange / finalEnhancedCoinDetails.length;
    }

    // 增强 latestRound，添加 average_change 字段
    const enhancedLatestRound = latestRound ? {
      ...latestRound,
      average_change: averageChange
    } : null;

    return {
      latestRound: enhancedLatestRound,
      coinDetails: finalEnhancedCoinDetails,
      todayStats,
      extremes,
      priorities: enhancedPriorities, // 使用动态计算优先级等级的数据
      // 🆕 新增统计数据
      specialStats: {
        change24hOver10Up,
        change24hOver10Down,
        change24hOver10UpPercent,
        change24hOver10DownPercent,
        todayNewHighCount,
        todayNewLowCount
      }
    };
  }

  // 获取指定轮次的仪表板数据(用于历史回看)
  async getDashboardDataByRound(roundTime: string) {
    // 获取指定轮次统计
    const roundStat = await this.coinService.getRoundStatByTime(roundTime);
    
    if (!roundStat) {
      throw new Error('指定轮次不存在');
    }

    // 获取指定轮次的币种详情
    const coinDetails = await this.coinService.getLatestCoinDetails(roundTime);

    // 获取该轮次日期的统计（将UTC时间转换为北京时间日期）
    const date = convertUTCtoBeijingDateString(roundTime); // 🔥 转换为北京时间日期
    const todayStats = await this.coinService.getTodayStats(date);

    // 获取极值数据(使用当前最新的,因为极值会持续更新)
    const extremes = await this.coinService.getAllPriceExtremes();

    // 获取优先级(使用当前最新的)
    const priorities = await this.coinService.getAllCoinPriorities();

    // 🆕 计算该轮次的specialStats（用于历史回看）
    const totalCoins = coinDetails.length;
    const change24hOver10Up = coinDetails.filter((coin: any) => coin.change_24h >= 10).length;
    const change24hOver10Down = coinDetails.filter((coin: any) => coin.change_24h <= -10).length;
    const change24hOver10UpPercent = totalCoins > 0 ? ((change24hOver10Up / totalCoins) * 100).toFixed(1) : '0.0';
    const change24hOver10DownPercent = totalCoins > 0 ? ((change24hOver10Down / totalCoins) * 100).toFixed(1) : '0.0';

    // 🆕 查询该日期的创新高/新低的总次数
    const todayNewHighCount = await this.coinService.getTodayExtremeCount(date, 'high');
    const todayNewLowCount = await this.coinService.getTodayExtremeCount(date, 'low');

    return {
      latestRound: roundStat,
      coinDetails,
      todayStats,
      extremes,
      priorities,
      specialStats: {
        change24hOver10Up,
        change24hOver10Down,
        change24hOver10UpPercent,
        change24hOver10DownPercent,
        todayNewHighCount,
        todayNewLowCount
      },
      isHistorical: true,
      historicalRoundTime: roundTime
    };
  }
}

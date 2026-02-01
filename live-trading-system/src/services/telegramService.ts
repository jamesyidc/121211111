// Telegram 通知服务
export class TelegramService {
  private botToken: string;
  private chatId: string;
  private apiUrl: string;

  constructor(botToken: string, chatId: string) {
    this.botToken = botToken;
    this.chatId = chatId;
    this.apiUrl = `https://api.telegram.org/bot${botToken}`;
  }

  // 发送预警消息到 Telegram
  async sendAlert(alert: any, klineData: any): Promise<boolean> {
    try {
      // 构建消息内容
      const message = this.buildAlertMessage(alert, klineData);
      
      // 发送到 Telegram
      const response = await fetch(`${this.apiUrl}/sendMessage`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          chat_id: this.chatId,
          text: message,
          parse_mode: 'HTML',
        }),
      });

      const result = await response.json();
      
      if (!result.ok) {
        console.error('❌ Telegram发送失败:', JSON.stringify(result));
        console.error('   消息内容预览:', message.substring(0, 200));
        return false;
      }

      console.log(`✅ 预警已发送到Telegram: ${alert.symbol} ${alert.time}`);
      return true;
    } catch (error) {
      console.error('❌ Telegram发送异常:', error);
      return false;
    }
  }

  // 构建预警消息
  private buildAlertMessage(alert: any, klineData: any): string {
    // 计算波动百分比
    const volatility = klineData.high && klineData.low && klineData.low > 0
      ? (((klineData.high - klineData.low) / klineData.low) * 100).toFixed(2)
      : '0.00';

    // 计算SAR差值
    const sarDiff = klineData.sar && klineData.close
      ? (klineData.close - klineData.sar).toFixed(2)
      : '0.00';

    // 判断新高新低
    const isNewHigh = klineData.rsi_5min && klineData.rsi_5min > 80 ? '✅' : '❌';
    const isNewLow = klineData.rsi_5min && klineData.rsi_5min < 20 ? '✅' : '❌';

    // 状态（基于触发条件）
    const status = alert.triggers.join(' + ');

    // 构建消息
    const message = `⚡️<b>交易预警</b>⚡️

📌 <b>币种:</b> ${alert.symbol || klineData.symbol}
🕒 <b>时间:</b> ${alert.time || klineData.time}
📊 <b>信号:</b> ${klineData.signal || '-'}
💹 <b>开盘:</b> ${klineData.open?.toFixed(4) || '-'}
📈 <b>最高:</b> ${klineData.high?.toFixed(4) || '-'}
📉 <b>最低:</b> ${klineData.low?.toFixed(4) || '-'}
🔔 <b>收盘:</b> ${klineData.close?.toFixed(4) || '-'}
📦 <b>成交量:</b> ${alert.data.volume || klineData.volume}
📐 <b>波动:</b> ${volatility}%
📉 <b>涨跌幅:</b> ${alert.data.changePercent || klineData.change}
📍 <b>SAR:</b> ${klineData.sar?.toFixed(4) || '-'} (差值:${sarDiff})
📊 <b>RSI(5m):</b> ${alert.data.rsi5min || klineData.rsi_5min || '-'}
📊 <b>RSI(1h):</b> ${klineData.rsi_1h || '-'}
📌 <b>状态:</b> ${status}
🚨 <b>新高:</b> ${isNewHigh}
🚨 <b>新低:</b> ${isNewLow}

🔔 <b>触发条件:</b>
${alert.triggers.map((t: string) => `• ${t}`).join('\n')}

💡 <b>量能级别:</b> ${alert.data.volumeLevel}
⚡️ <b>SAR变化:</b> ${alert.data.sarChangePercent}`;

    return message;
  }

  // 批量发送多个预警
  async sendMultipleAlerts(alerts: any[], klineDataMap: Map<number, any>): Promise<number> {
    let successCount = 0;

    console.log(`📨 准备发送 ${alerts.length} 条预警到Telegram...`);
    
    for (let i = 0; i < alerts.length; i++) {
      const alert = alerts[i];
      const klineData = klineDataMap.get(alert.index);
      if (klineData) {
        console.log(`   [${i+1}/${alerts.length}] ${alert.symbol} ${alert.time} (index=${alert.index})`);
        const success = await this.sendAlert(alert, klineData);
        if (success) {
          successCount++;
        }
        
        // 避免发送过快，每条消息间隔1秒
        await this.delay(1000);
      } else {
        console.log(`   [${i+1}/${alerts.length}] ⚠️  跳过：找不到K线数据 (index=${alert.index})`);
      }
    }

    console.log(`📨 发送完成：成功 ${successCount}/${alerts.length} 条`);
    return successCount;
  }

  // 延迟函数
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // 测试连接
  async testConnection(): Promise<boolean> {
    try {
      const response = await fetch(`${this.apiUrl}/getMe`);
      const result = await response.json();
      
      if (result.ok) {
        console.log('✅ Telegram连接成功:', result.result.username);
        return true;
      } else {
        console.error('❌ Telegram连接失败:', result);
        return false;
      }
    } catch (error) {
      console.error('❌ Telegram连接异常:', error);
      return false;
    }
  }

  // 发送持仓提醒（多单见顶/空单见底）
  async sendPositionAlert(alert: any): Promise<boolean> {
    try {
      const message = this.buildPositionAlertMessage(alert);
      
      const response = await fetch(`${this.apiUrl}/sendMessage`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          chat_id: this.chatId,
          text: message,
          parse_mode: 'HTML',
        }),
      });

      const result = await response.json();
      
      if (!result.ok) {
        console.error('❌ 持仓提醒发送失败:', JSON.stringify(result));
        return false;
      }

      console.log(`✅ 持仓提醒已发送: ${alert.position.symbol} ${alert.alertType}`);
      return true;
    } catch (error) {
      console.error('❌ 持仓提醒发送异常:', error);
      return false;
    }
  }

  // 构建持仓提醒消息
  private buildPositionAlertMessage(alert: any): string {
    const { position, alertType, klineTime, currentPrice, sarChangePercent, changePercent, rsi5min, profitPercent } = alert;
    
    const isLongTop = alertType === 'LONG_TOP';
    const emoji = isLongTop ? '🔴' : '🟢';
    const title = isLongTop ? '多单见顶预警' : '空单见底预警';
    const action = isLongTop ? '建议止盈' : '建议止盈';
    
    return `
${emoji} <b>${title}</b> ${emoji}

📊 <b>币种</b>: ${position.symbol}
💰 <b>持仓类型</b>: ${position.position_type === 'LONG' ? '多单🟢' : '空单🔴'}
🎯 <b>开仓价格</b>: $${position.entry_price.toFixed(4)}
💵 <b>当前价格</b>: $${currentPrice.toFixed(4)}
📈 <b>盈亏</b>: ${parseFloat(profitPercent) >= 0 ? '+' : ''}${profitPercent}%

⚠️ <b>预警信号</b>:
├─ SAR变化: ${sarChangePercent.toFixed(2)}%
├─ 涨跌幅: ${changePercent.toFixed(2)}%
└─ RSI(5m): ${rsi5min.toFixed(2)} ${isLongTop ? '(超买⬆️)' : '(超卖⬇️)'}

🕐 <b>触发时间</b>: ${klineTime}

${isLongTop ? 
  '⚠️ <b>多单警告</b>: SAR上涨但价格回调，RSI超买(>70)，可能见顶！' : 
  '⚠️ <b>空单警告</b>: SAR下跌但价格反弹，RSI超卖(<30)，可能见底！'
}

💡 <b>${action}</b>

${position.notes ? `📝 备注: ${position.notes}` : ''}
    `.trim();
  }

  // 🆕 发送买卖点信号
  async sendTradingSignal(signal: any): Promise<boolean> {
    try {
      const message = this.buildTradingSignalMessage(signal);
      
      const response = await fetch(`${this.apiUrl}/sendMessage`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          chat_id: this.chatId,
          text: message,
          parse_mode: 'HTML',
        }),
      });

      const result = await response.json();
      
      if (!result.ok) {
        console.error('❌ 买卖点信号发送失败:', JSON.stringify(result));
        return false;
      }

      console.log(`✅ 买卖点信号已发送: ${signal.symbol} ${signal.signal_type} ${signal.signal_time}`);
      return true;
    } catch (error) {
      console.error('❌ 买卖点信号发送异常:', error);
      return false;
    }
  }

  // 🆕 构建买卖点信号消息
  private buildTradingSignalMessage(signal: any): string {
    const isBuy = signal.signal_type === 'BUY';
    const emoji = isBuy ? '🟢' : '🔴';
    const typeText = isBuy ? '做多信号' : '做空信号';
    
    // 解析details（可能是JSON字符串）
    let details = signal.details;
    if (typeof details === 'string') {
      try {
        details = JSON.parse(details);
      } catch (e) {
        details = {};
      }
    }
    
    // 判断是否是主升信号
    const isMainRise = signal.reason && signal.reason.includes('主升信号');
    const titleEmoji = isMainRise ? '🚀' : emoji;
    const title = isMainRise ? '主升信号 🚀' : typeText;
    
    return `
${titleEmoji} <b>${title}</b> ${titleEmoji}

📊 <b>币种</b>: ${signal.symbol}
🕒 <b>时间</b>: ${signal.signal_time}
💰 <b>价格</b>: $${parseFloat(signal.price).toFixed(4)}
⚡️ <b>信号强度</b>: ${signal.strength}/100
📝 <b>原因</b>: ${signal.reason || '-'}

📊 <b>技术指标</b>:
├─ RSI(5m): ${details.rsi5min || '-'}
├─ 波动率: ${details.volatility || '-'}
├─ 量能: ${details.volumeLevel || '-'}
└─ SAR变化: ${details.sarChangePercent || '-'}

${isMainRise ? `
🚀 <b>主升信号特征</b>:
• 币种优先级: ${details.coinLevel || '-'}
• 价格位置: ${details.pricePosition ? (details.pricePosition * 100).toFixed(1) + '%' : '-'}
• 下跌幅度: ${details.priceDropPercent || '-'}
• 震荡收敛: ${details.convergenceCount || '-'}
` : ''}

⏰ <b>持有观察</b>: ${signal.keep_bars || 0} 根K线
    `.trim();
  }

  // 🆕 发送恐慌清洗指标预警
  async sendLiquidationPanicAlert(data: any): Promise<boolean> {
    try {
      const message = this.buildLiquidationPanicMessage(data);
      
      const response = await fetch(`${this.apiUrl}/sendMessage`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          chat_id: this.chatId,
          text: message,
          parse_mode: 'HTML',
        }),
      });

      const result = await response.json();
      
      if (!result.ok) {
        console.error('❌ 恐慌清洗预警发送失败:', JSON.stringify(result));
        return false;
      }

      console.log(`✅ 恐慌清洗预警已发送: 比率 ${(data.ratio * 100).toFixed(2)}%`);
      return true;
    } catch (error) {
      console.error('❌ 恐慌清洗预警发送异常:', error);
      return false;
    }
  }

  // 🆕 构建恐慌清洗指标预警消息
  private buildLiquidationPanicMessage(data: any): string {
    const { count24h, amount24h, totalOI, ratio, updateTime } = data;
    const ratioPercent = (ratio * 100).toFixed(2);
    const countInWan = (count24h / 10000).toFixed(2);
    
    // 根据比率判断恐慌等级
    let level = '';
    let emoji = '';
    if (ratio < 0.04) {
      level = '极端恐慌';
      emoji = '🔴🔴🔴';
    } else if (ratio < 0.10) {
      level = '恐慌';
      emoji = '🟠🟠';
    } else if (ratio < 0.15) {
      level = '警惕';
      emoji = '🟡';
    } else {
      level = '正常';
      emoji = '🟢';
    }
    
    return `
${emoji} <b>恐慌清洗指标预警</b> ${emoji}

⚠️ <b>警戒级别</b>: ${level}
📊 <b>恐慌清洗比率</b>: ${ratioPercent}%

📈 <b>市场数据</b>:
├─ 24H爆仓人数: ${countInWan}万人 (${count24h.toLocaleString()}人)
├─ 24H爆仓金额: $${amount24h.toFixed(2)}亿
├─ 全网持仓量: $${totalOI.toFixed(2)}亿
└─ 计算公式: 爆仓人数(万) ÷ 持仓量(亿$)

${ratio < 0.15 ? `
⚠️ <b>预警说明</b>:
恐慌清洗比率已低于15%警戒线，市场可能处于恐慌状态。
建议密切关注市场情绪变化，谨慎操作。
` : ''}

${ratio < 0.04 ? `
🚨 <b>极端预警</b>:
比率低于4%阈值，市场处于极端恐慌状态！
大量爆仓表明强制平仓压力巨大，注意风险控制！
` : ''}

🕒 <b>更新时间</b>: ${new Date(updateTime).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}

💡 <b>建议</b>: ${ratio < 0.10 ? '市场恐慌时可能是抄底机会，但需谨慎判断' : '继续观察市场情绪变化'}
    `.trim();
  }
}

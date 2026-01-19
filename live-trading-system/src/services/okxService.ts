import CryptoJS from 'crypto-js'

/**
 * OKX API 服务类
 * 用于实盘交易 - 限价/市价委托、止盈止损
 */
interface OKXServiceConfig {
  apiKey: string
  secretKey: string
  passphrase: string
  isTestnet?: boolean
}

export class OKXService {
  private apiKey: string
  private secretKey: string
  private passphrase: string
  private baseUrl: string
  private isTestnet: boolean

  constructor(config: OKXServiceConfig | string, secretKey?: string, passphrase?: string, isTestnet: boolean = false) {
    // Support both object and individual parameters
    if (typeof config === 'object') {
      this.apiKey = config.apiKey
      this.secretKey = config.secretKey
      this.passphrase = config.passphrase
      this.isTestnet = config.isTestnet || false
    } else {
      this.apiKey = config
      this.secretKey = secretKey!
      this.passphrase = passphrase!
      this.isTestnet = isTestnet
    }
    
    this.baseUrl = this.isTestnet 
      ? 'https://www.okx.com'  // OKX 测试网已停用，使用主网但建议用模拟盘
      : 'https://www.okx.com'
  }

  /**
   * 生成签名
   */
  private generateSignature(timestamp: string, method: string, requestPath: string, body: string = ''): string {
    const message = timestamp + method + requestPath + body
    return CryptoJS.enc.Base64.stringify(CryptoJS.HmacSHA256(message, this.secretKey))
  }

  /**
   * 生成请求头
   */
  private getHeaders(method: string, requestPath: string, body: string = ''): HeadersInit {
    const timestamp = new Date().toISOString()
    const sign = this.generateSignature(timestamp, method, requestPath, body)
    
    // OKX API 要求 passphrase 也需要用 HMAC-SHA256 加密后 Base64 编码
    const encryptedPassphrase = CryptoJS.enc.Base64.stringify(
      CryptoJS.HmacSHA256(this.passphrase, this.secretKey)
    )
    
    return {
      'Content-Type': 'application/json',
      'OK-ACCESS-KEY': this.apiKey,
      'OK-ACCESS-SIGN': sign,
      'OK-ACCESS-TIMESTAMP': timestamp,
      'OK-ACCESS-PASSPHRASE': encryptedPassphrase,
    }
  }

  /**
   * 发送API请求
   */
  private async request(method: string, endpoint: string, body?: any): Promise<any> {
    const requestPath = `/api/v5${endpoint}`
    const bodyStr = body ? JSON.stringify(body) : ''
    
    const response = await fetch(`${this.baseUrl}${requestPath}`, {
      method,
      headers: this.getHeaders(method, requestPath, bodyStr),
      body: bodyStr || undefined,
    })

    const data = await response.json()
    
    if (data.code !== '0') {
      throw new Error(`OKX API Error: ${data.msg} (code: ${data.code})`)
    }
    
    return data
  }

  /**
   * 获取账户余额
   */
  async getBalance(): Promise<any> {
    return await this.request('GET', '/account/balance')
  }

  /**
   * 获取账户余额（格式化）
   */
  async getAccountBalance(): Promise<{ availableBalance: number; totalEquity: number }> {
    const data = await this.request('GET', '/account/balance')
    
    if (data.data && data.data.length > 0) {
      const accountData = data.data[0]
      const usdtDetail = accountData.details?.find((d: any) => d.ccy === 'USDT')
      
      return {
        availableBalance: parseFloat(usdtDetail?.availBal || accountData.totalEq || '0'),
        totalEquity: parseFloat(accountData.totalEq || '0')
      }
    }
    
    return { availableBalance: 0, totalEquity: 0 }
  }

  /**
   * 获取持仓信息
   */
  async getPositions(instType: string = 'SWAP'): Promise<any[]> {
    const data = await this.request('GET', `/account/positions?instType=${instType}`)
    return data.data || []
  }

  /**
   * 设置杠杆倍数
   * @param instId 产品ID，如 BTC-USDT-SWAP
   * @param lever 杠杆倍数 3, 5, 10, 20
   * @param mgnMode 保证金模式 cross(全仓) isolated(逐仓)
   */
  async setLeverage(instId: string, lever: number, mgnMode: string = 'cross'): Promise<any> {
    return await this.request('POST', '/account/set-leverage', {
      instId,
      lever: lever.toString(),
      mgnMode,
    })
  }

  /**
   * 下单 - 限价委托
   * @param instId 产品ID，如 BTC-USDT-SWAP
   * @param side buy(买入做多) sell(卖出做空)
   * @param sz 数量（币的数量）
   * @param px 委托价格
   * @param orderType 订单类型 limit(限价) opponent(对手价) optimal_limit_ioc(最优限价IOC)
   */
  async placeLimitOrder(params: {
    instId: string
    side: 'buy' | 'sell'
    sz: string
    px?: string
    tdMode: 'cross' | 'isolated'  // cross全仓 isolated逐仓
    orderType?: 'limit' | 'opponent' | 'optimal_limit_ioc'
  }): Promise<any> {
    const body = {
      instId: params.instId,
      tdMode: params.tdMode,
      side: params.side,
      ordType: params.orderType || 'limit',
      sz: params.sz,
      px: params.px,
    }
    
    return await this.request('POST', '/trade/order', body)
  }

  /**
   * 下单 - 市价委托
   */
  async placeMarketOrder(params: {
    instId: string
    side: 'buy' | 'sell'
    sz: string
    tdMode: 'cross' | 'isolated'
  }): Promise<any> {
    const body = {
      instId: params.instId,
      tdMode: params.tdMode,
      side: params.side,
      ordType: 'market',
      sz: params.sz,
    }
    
    return await this.request('POST', '/trade/order', body)
  }

  /**
   * 下单 - 对手价
   * @param level 档位 1-5
   */
  async placeOpponentOrder(params: {
    instId: string
    side: 'buy' | 'sell'
    sz: string
    tdMode: 'cross' | 'isolated'
    level: 1 | 5  // 对手价1档或5档
  }): Promise<any> {
    // OKX的对手价使用 opponent 或 opponent5
    const ordType = params.level === 1 ? 'opponent' : 'opponent5'
    
    const body = {
      instId: params.instId,
      tdMode: params.tdMode,
      side: params.side,
      ordType,
      sz: params.sz,
    }
    
    return await this.request('POST', '/trade/order', body)
  }

  /**
   * 下单 - 同向价
   * @param level 档位 1-5
   */
  async placeOptimalOrder(params: {
    instId: string
    side: 'buy' | 'sell'
    sz: string
    tdMode: 'cross' | 'isolated'
    level: 1 | 5  // 同向价1档或5档
  }): Promise<any> {
    // OKX的同向价使用 optimal_limit_ioc
    const body = {
      instId: params.instId,
      tdMode: params.tdMode,
      side: params.side,
      ordType: 'optimal_limit_ioc',
      sz: params.sz,
    }
    
    return await this.request('POST', '/trade/order', body)
  }

  /**
   * 设置止盈止损 - 固定数量
   * @param instId 产品ID
   * @param posSide 持仓方向 long(多) short(空)
   * @param tpTriggerPx 止盈触发价
   * @param slTriggerPx 止损触发价
   * @param tpOrdPx 止盈委托价（可选，不填则市价）
   * @param slOrdPx 止损委托价（可选，不填则市价）
   * @param sz 数量（币的数量）
   */
  async setStopOrder(params: {
    instId: string
    posSide: 'long' | 'short'
    sz: string
    tpTriggerPx?: string  // 止盈触发价
    tpOrdPx?: string      // 止盈委托价
    slTriggerPx?: string  // 止损触发价
    slOrdPx?: string      // 止损委托价
  }): Promise<any> {
    const body: any = {
      instId: params.instId,
      tdMode: 'cross',
      side: params.posSide === 'long' ? 'sell' : 'buy',  // 平仓方向相反
      ordType: 'conditional',
      sz: params.sz,
    }

    // 止盈
    if (params.tpTriggerPx) {
      body.tpTriggerPx = params.tpTriggerPx
      body.tpOrdPx = params.tpOrdPx || '-1'  // -1 表示市价
    }

    // 止损
    if (params.slTriggerPx) {
      body.slTriggerPx = params.slTriggerPx
      body.slOrdPx = params.slOrdPx || '-1'  // -1 表示市价
    }

    return await this.request('POST', '/trade/order-algo', body)
  }

  /**
   * 获取最新价格
   */
  async getTicker(instId: string): Promise<any> {
    return await this.request('GET', `/market/ticker?instId=${instId}`)
  }

  /**
   * 获取深度数据（用于计算对手价、同向价）
   */
  async getOrderBook(instId: string, sz: number = 5): Promise<any> {
    return await this.request('GET', `/market/books?instId=${instId}&sz=${sz}`)
  }

  /**
   * 撤单
   */
  async cancelOrder(instId: string, ordId: string): Promise<any> {
    return await this.request('POST', '/trade/cancel-order', {
      instId,
      ordId,
    })
  }

  /**
   * 获取未成交订单列表
   */
  async getPendingOrders(instId?: string): Promise<any> {
    const params = instId ? `?instId=${instId}` : ''
    return await this.request('GET', `/trade/orders-pending${params}`)
  }

  /**
   * 获取历史订单
   */
  async getOrderHistory(instId?: string, limit: number = 100): Promise<any> {
    let params = `?instType=SWAP&limit=${limit}`
    if (instId) {
      params += `&instId=${instId}`
    }
    return await this.request('GET', `/trade/orders-history${params}`)
  }

  /**
   * 批量下单
   */
  async batchOrders(orders: any[]): Promise<any> {
    return await this.request('POST', '/trade/batch-orders', orders)
  }

  /**
   * 一键平仓
   */
  async closePosition(instId: string, posSide: 'long' | 'short', mgnMode: string = 'cross'): Promise<any> {
    return await this.request('POST', '/trade/close-position', {
      instId,
      mgnMode,
      posSide,
    })
  }

  /**
   * 设置持仓的止盈止损 - 全仓模式（全部仓位，按涨跌幅触发）
   * OKX API: /api/v5/trade/order-algo
   * 
   * ⚠️ 重要发现：OKX要求止盈和止损必须分开两次API调用！
   * 如果在同一个请求中同时设置tpTriggerPx和slTriggerPx，只有止损会生效。
   * 
   * 解决方案：分别调用两次API，一次设置止盈，一次设置止损
   */
  async setFullTPSL(params: {
    symbol: string;
    side: 'long' | 'short';
    takeProfit?: {
      triggerPrice?: string;
      profitRate?: number;
    };
    stopLoss?: {
      triggerPrice?: string;
      lossRate?: number;
    };
  }): Promise<any> {
    const { symbol, side, takeProfit, stopLoss } = params;
    
    // 获取当前持仓信息
    const instId = `${symbol}-USDT-SWAP`;
    const positions = await this.getPositions('SWAP');
    console.log('🔍 查询持仓列表:', positions);
    
    // 查找匹配的持仓（instId + posSide）
    const position = positions.find((p: any) => 
      p.instId === instId && p.posSide === side
    );
    
    console.log('🎯 匹配持仓:', position);
    
    if (!position || parseFloat(position.pos) === 0) {
      const availablePositions = positions.map((p: any) => 
        `${p.instId} ${p.posSide} pos=${p.pos}`
      ).join(', ');
      throw new Error(`未找到持仓 [${instId} ${side}]。当前持仓: ${availablePositions || '无'}`);
    }
    
    const entryPrice = parseFloat(position.avgPx);
    console.log(`💰 入场价: ${entryPrice}`);
    
    const results: any[] = [];
    
    // 🔧 关键修复：分开设置止盈和止损
    
    // 1️⃣ 先设置止盈
    if (takeProfit) {
      console.log('\n1️⃣ 设置止盈订单...');
      
      const tpBody: any = {
        instId,
        tdMode: 'cross',
        side: side === 'long' ? 'sell' : 'buy',
        ordType: 'conditional',
        posSide: side
      };
      
      if (takeProfit.triggerPrice) {
        tpBody.tpTriggerPx = takeProfit.triggerPrice;
        tpBody.tpTriggerPxType = 'last';
        tpBody.tpOrdPx = '-1';
      } else if (takeProfit.profitRate) {
        const tpPrice = side === 'long'
          ? entryPrice * (1 + takeProfit.profitRate / 100)
          : entryPrice * (1 - takeProfit.profitRate / 100);
        tpBody.tpTriggerPx = tpPrice.toFixed(6);
        tpBody.tpTriggerPxType = 'last';
        tpBody.tpOrdPx = '-1';
      }
      
      // 关键：必须设置sz参数，指定平仓数量
      tpBody.sz = position.pos;
      
      console.log('📊 止盈参数:', tpBody);
      console.log(`   止盈价: ${tpBody.tpTriggerPx} (${takeProfit.profitRate}%)`);
      
      try {
        const tpResult = await this.request('POST', '/api/v5/trade/order-algo', tpBody);
        console.log('✅ 止盈订单设置成功:', JSON.stringify(tpResult, null, 2));
        
        // 检查OKX返回的详细信息
        if (tpResult.code !== '0') {
          console.error(`⚠️ OKX返回异常: code=${tpResult.code}, msg=${tpResult.msg}`);
          results.push({ type: 'take_profit', error: `OKX错误: ${tpResult.msg}` });
        } else {
          results.push({ type: 'take_profit', result: tpResult });
        }
      } catch (error: any) {
        console.error('❌ 止盈订单设置失败:', error.message);
        results.push({ type: 'take_profit', error: error.message });
      }
    }
    
    // 2️⃣ 再设置止损
    if (stopLoss) {
      console.log('\n2️⃣ 设置止损订单...');
      
      const slBody: any = {
        instId,
        tdMode: 'cross',
        side: side === 'long' ? 'sell' : 'buy',
        ordType: 'conditional',
        posSide: side
      };
      
      if (stopLoss.triggerPrice) {
        slBody.slTriggerPx = stopLoss.triggerPrice;
        slBody.slTriggerPxType = 'last';
        slBody.slOrdPx = '-1';
      } else if (stopLoss.lossRate) {
        const slPrice = side === 'long'
          ? entryPrice * (1 - Math.abs(stopLoss.lossRate) / 100)
          : entryPrice * (1 + Math.abs(stopLoss.lossRate) / 100);
        slBody.slTriggerPx = slPrice.toFixed(6);
        slBody.slTriggerPxType = 'last';
        slBody.slOrdPx = '-1';
      }
      
      // 关键：必须设置sz参数，指定平仓数量
      slBody.sz = position.pos;
      
      console.log('📊 止损参数:', slBody);
      console.log(`   止损价: ${slBody.slTriggerPx} (${stopLoss.lossRate}%)`);
      
      try {
        const slResult = await this.request('POST', '/api/v5/trade/order-algo', slBody);
        console.log('✅ 止损订单设置成功:', JSON.stringify(slResult, null, 2));
        
        // 检查OKX返回的详细信息
        if (slResult.code !== '0') {
          console.error(`⚠️ OKX返回异常: code=${slResult.code}, msg=${slResult.msg}`);
          results.push({ type: 'stop_loss', error: `OKX错误: ${slResult.msg}` });
        } else {
          results.push({ type: 'stop_loss', result: slResult });
        }
      } catch (error: any) {
        console.error('❌ 止损订单设置失败:', error.message);
        results.push({ type: 'stop_loss', error: error.message });
      }
    }
    
    // 返回结果
    const tpSuccess = results.find(r => r.type === 'take_profit' && r.result);
    const slSuccess = results.find(r => r.type === 'stop_loss' && r.result);
    const tpError = results.find(r => r.type === 'take_profit' && r.error);
    const slError = results.find(r => r.type === 'stop_loss' && r.error);
    
    console.log('\n📋 最终结果:');
    console.log(`   止盈: ${tpSuccess ? '✅ 成功' : tpError ? '❌ 失败' : '⊘ 未设置'}`);
    console.log(`   止损: ${slSuccess ? '✅ 成功' : slError ? '❌ 失败' : '⊘ 未设置'}`);
    
    if (tpError || slError) {
      const errors = [];
      if (tpError) errors.push(`止盈: ${tpError.error}`);
      if (slError) errors.push(`止损: ${slError.error}`);
      
      // 如果有一个成功，就算部分成功
      if (tpSuccess || slSuccess) {
        return {
          code: '0',
          msg: '部分成功',
          data: results,
          warning: errors.join('; ')
        };
      } else {
        throw new Error(`止盈止损设置失败: ${errors.join('; ')}`);
      }
    }
    
    return {
      code: '0',
      msg: '止盈止损设置成功',
      data: results
    };
  }

  /**
   * 计算百分比对应的数量
   * @param balance 可用余额 USDT
   * @param price 当前价格
   * @param percentage 百分比 0.1, 0.25, 0.33, 0.5, 1.0
   * @param leverage 杠杆倍数
   */
  calculateSizeByPercentage(balance: number, price: number, percentage: number, leverage: number): number {
    // 可用金额 = 余额 * 百分比 * 杠杆倍数
    const availableAmount = balance * percentage * leverage
    // 币的数量 = 可用金额 / 价格
    return availableAmount / price
  }

  /**
   * 根据收益率计算目标价格
   * @param entryPrice 开仓价
   * @param profitRate 收益率（百分比，如 5 表示5%）
   * @param isLong 是否做多
   */
  calculateTargetPrice(entryPrice: number, profitRate: number, isLong: boolean): number {
    const rate = profitRate / 100
    if (isLong) {
      return entryPrice * (1 + rate)
    } else {
      return entryPrice * (1 - rate)
    }
  }
}

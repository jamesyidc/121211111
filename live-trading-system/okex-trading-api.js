/**
 * OKX实盘交易API模块
 * 支持27个交易对的USDT永续合约交易
 */

// 支持的27个交易对
const SUPPORTED_SYMBOLS = [
  'BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'LTC', 'DOGE', 'SUI', 'TRX', 'TON',
  'ETC', 'BCH', 'HBAR', 'XLM', 'FIL', 'ADA', 'LINK', 'CRO', 'DOT', 'UNI',
  'NEAR', 'APT', 'CFX', 'CRV', 'STX', 'LDO', 'TAO'
];

// 支持的杠杆倍数
const LEVERAGE_OPTIONS = [3, 5, 10, 20];

// 默认杠杆倍数
const DEFAULT_LEVERAGE = 10;

class OKXTradingAPI {
  constructor(apiKey, apiSecret, passphrase, isTestnet = false) {
    this.apiKey = apiKey;
    this.apiSecret = apiSecret;
    this.passphrase = passphrase;
    this.baseURL = 'https://www.okx.com';  // OKX实盘API
  }

  /**
   * 生成签名
   */
  async sign(timestamp, method, requestPath, body = '') {
    const message = timestamp + method + requestPath + body;
    
    // 使用Web Crypto API
    const encoder = new TextEncoder();
    const keyData = encoder.encode(this.apiSecret);
    const messageData = encoder.encode(message);
    
    const key = await crypto.subtle.importKey(
      'raw',
      keyData,
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign']
    );
    
    const signature = await crypto.subtle.sign('HMAC', key, messageData);
    const base64Signature = btoa(String.fromCharCode(...new Uint8Array(signature)));
    
    return base64Signature;
  }

  /**
   * 生成请求头
   */
  async getHeaders(method, requestPath, body = '') {
    const timestamp = new Date().toISOString();
    const sign = await this.sign(timestamp, method, requestPath, body);
    
    return {
      'OK-ACCESS-KEY': this.apiKey,
      'OK-ACCESS-SIGN': sign,
      'OK-ACCESS-TIMESTAMP': timestamp,
      'OK-ACCESS-PASSPHRASE': this.passphrase,
      'Content-Type': 'application/json',
    };
  }

  /**
   * 发送请求
   */
  async request(method, endpoint, data = null) {
    try {
      const requestPath = `/api/v5${endpoint}`;
      const body = data ? JSON.stringify(data) : '';
      const headers = await this.getHeaders(method, requestPath, body);

      // 使用fetch API替代axios（Cloudflare Workers兼容）
      const url = `${this.baseURL}${requestPath}`;
      const response = await fetch(url, {
        method,
        headers: {
          ...headers,
          'Content-Type': 'application/json'
        },
        body: method !== 'GET' && data ? body : undefined,
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('OKX API Error:', response.status, errorText);
        throw new Error(`OKX API Error: ${response.status} ${errorText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('OKX API Request Failed:', error.message);
      throw error;
    }
  }

  /**
   * 获取交易对盘口数据
   * @param {string} symbol - 交易对 (如: BTC)
   * @param {number} depth - 深度 (1, 5, 10, 20)
   */
  async getOrderBook(symbol, depth = 5) {
    const instId = `${symbol}-USDT-SWAP`;
    const endpoint = `/market/books?instId=${instId}&sz=${depth}`;
    return await this.request('GET', endpoint);
  }

  /**
   * 获取账户余额
   */
  async getBalance() {
    return await this.request('GET', '/account/balance');
  }

  /**
   * 设置杠杆倍数
   * @param {string} symbol - 交易对
   * @param {number} leverage - 杠杆倍数 (3, 5, 10, 20)
   * @param {string} marginMode - 保证金模式 ('cross'=全仓, 'isolated'=逐仓)
   */
  async setLeverage(symbol, leverage = DEFAULT_LEVERAGE, marginMode = 'cross') {
    if (!LEVERAGE_OPTIONS.includes(leverage)) {
      throw new Error(`不支持的杠杆倍数: ${leverage}，仅支持: ${LEVERAGE_OPTIONS.join(', ')}`);
    }

    const instId = `${symbol}-USDT-SWAP`;
    return await this.request('POST', '/account/set-leverage', {
      instId,
      lever: leverage.toString(),
      mgnMode: marginMode,
    });
  }

  /**
   * 限价委托下单
   * @param {object} params - 订单参数
   * @param {string} params.symbol - 交易对
   * @param {string} params.side - 方向 ('buy'=做多, 'sell'=做空)
   * @param {string} params.priceType - 价格类型 ('opponent1', 'opponent5', 'optimal1', 'optimal5')
   * @param {number} params.usdtAmount - USDT数量
   * @param {number} params.percentage - 百分比 (10, 25, 33, 50, 100)
   * @param {number} params.leverage - 杠杆倍数
   */
  async limitOrder(params) {
    const { symbol, side, priceType, usdtAmount, percentage, leverage = DEFAULT_LEVERAGE } = params;
    
    // 确保持仓模式设置为双向持仓模式
    console.log('尝试设置持仓模式为 long_short_mode...');
    try {
      const result = await this.setPositionMode('long_short_mode');
      console.log('设置持仓模式结果:', JSON.stringify(result, null, 2));
    } catch (error) {
      // 如果已经设置过，会返回错误，忽略即可
      console.log('设置持仓模式失败或已设置:', error.message);
      if (error.response) {
        console.log('错误详情:', JSON.stringify(error.response.data, null, 2));
      }
    }
    
    // 设置杠杆
    await this.setLeverage(symbol, leverage);

    // 获取盘口数据计算价格
    const orderBook = await this.getOrderBook(symbol, priceType.includes('5') ? 5 : 1);
    const price = this.calculateLimitPrice(orderBook, side, priceType);

    // 计算实际USDT数量
    let actualAmount = usdtAmount;
    if (percentage) {
      const balance = await this.getBalance();
      const availableUSDT = this.getAvailableUSDT(balance);
      actualAmount = (availableUSDT * percentage) / 100;
    }

    // 计算合约张数 (OKX永续合约以张为单位)
    const contractSize = await this.getContractSize(symbol);
    const sz = Math.floor((actualAmount * leverage) / (price * contractSize));

    const instId = `${symbol}-USDT-SWAP`;
    return await this.request('POST', '/trade/order', {
      instId,
      tdMode: 'cross', // 全仓模式
      side: side === 'buy' ? 'buy' : 'sell',
      ordType: 'limit',
      px: price.toString(),
      sz: sz.toString(),
      posSide: side === 'buy' ? 'long' : 'short',
    });
  }

  /**
   * 市价委托下单
   * @param {object} params - 订单参数
   * @param {string} params.symbol - 交易对
   * @param {string} params.side - 方向 ('buy'=做多, 'sell'=做空)
   * @param {number} params.usdtAmount - USDT数量
   * @param {number} params.percentage - 百分比 (10, 25, 33, 50, 100)
   * @param {number} params.leverage - 杠杆倍数
   */
  async marketOrder(params) {
    const { symbol, side, usdtAmount, percentage, leverage = DEFAULT_LEVERAGE } = params;
    
    // 确保持仓模式设置为双向持仓模式
    console.log('尝试设置持仓模式为 long_short_mode...');
    try {
      const result = await this.setPositionMode('long_short_mode');
      console.log('设置持仓模式结果:', JSON.stringify(result, null, 2));
    } catch (error) {
      // 如果已经设置过，会返回错误，忽略即可
      console.log('设置持仓模式失败或已设置:', error.message);
      if (error.response) {
        console.log('错误详情:', JSON.stringify(error.response.data, null, 2));
      }
    }
    
    // 设置杠杆
    await this.setLeverage(symbol, leverage);

    // 计算实际USDT数量
    let actualAmount = usdtAmount;
    if (percentage) {
      const balance = await this.getBalance();
      const availableUSDT = this.getAvailableUSDT(balance);
      actualAmount = (availableUSDT * percentage) / 100;
    }

    // 获取当前市价
    const ticker = await this.getTicker(symbol);
    const price = parseFloat(ticker.data[0].last);

    // 计算合约张数
    const contractSize = await this.getContractSize(symbol);
    const sz = Math.floor((actualAmount * leverage) / (price * contractSize));

    const instId = `${symbol}-USDT-SWAP`;
    return await this.request('POST', '/trade/order', {
      instId,
      tdMode: 'cross',
      side: side === 'buy' ? 'buy' : 'sell',
      ordType: 'market',
      sz: sz.toString(),
      posSide: side === 'buy' ? 'long' : 'short',
    });
  }

  /**
   * 设置止盈止损 - 固定数量
   * @param {object} params - 止盈止损参数
   * @param {string} params.symbol - 交易对
   * @param {string} params.side - 仓位方向 ('long', 'short')
   * @param {object} params.takeProfit - 止盈设置 { price, profitRate, percentage, usdtAmount }
   * @param {object} params.stopLoss - 止损设置 { price, lossRate, percentage, usdtAmount }
   */
  async setPartialTPSL(params) {
    const { symbol, side, takeProfit, stopLoss } = params;
    const instId = `${symbol}-USDT-SWAP`;
    const results = {};

    // 获取当前持仓
    const position = await this.getPosition(symbol);
    if (!position || position.pos === '0') {
      throw new Error('未找到持仓');
    }

    const currentPrice = parseFloat(position.last);
    const posSize = Math.abs(parseFloat(position.pos));

    // 设置止盈
    if (takeProfit) {
      let tpPrice = takeProfit.price;
      if (!tpPrice && takeProfit.profitRate) {
        tpPrice = side === 'long' 
          ? currentPrice * (1 + takeProfit.profitRate / 100)
          : currentPrice * (1 - takeProfit.profitRate / 100);
      }

      let tpSize = posSize;
      if (takeProfit.percentage) {
        tpSize = Math.floor(posSize * takeProfit.percentage / 100);
      }

      results.takeProfit = await this.request('POST', '/trade/order-algo', {
        instId,
        tdMode: 'cross',
        side: side === 'long' ? 'sell' : 'buy',
        ordType: 'conditional',
        sz: tpSize.toString(),
        posSide: side,
        tpTriggerPx: tpPrice.toString(),
        tpOrdPx: '-1', // 市价
      });
    }

    // 设置止损
    if (stopLoss) {
      let slPrice = stopLoss.price;
      if (!slPrice && stopLoss.lossRate) {
        slPrice = side === 'long'
          ? currentPrice * (1 - stopLoss.lossRate / 100)
          : currentPrice * (1 + stopLoss.lossRate / 100);
      }

      let slSize = posSize;
      if (stopLoss.percentage) {
        slSize = Math.floor(posSize * stopLoss.percentage / 100);
      }

      results.stopLoss = await this.request('POST', '/trade/order-algo', {
        instId,
        tdMode: 'cross',
        side: side === 'long' ? 'sell' : 'buy',
        ordType: 'conditional',
        sz: slSize.toString(),
        posSide: side,
        slTriggerPx: slPrice.toString(),
        slOrdPx: '-1', // 市价
      });
    }

    return results;
  }

  /**
   * 设置止盈止损 - 全部仓位
   * @param {object} params - 止盈止损参数
   * @param {string} params.symbol - 交易对
   * @param {string} params.side - 仓位方向 ('long', 'short')
   * @param {object} params.takeProfit - 止盈设置 { triggerPrice, profitRate }
   * @param {object} params.stopLoss - 止损设置 { triggerPrice, lossRate }
   */
  async setFullTPSL(params) {
    const { symbol, side, takeProfit, stopLoss } = params;
    const instId = `${symbol}-USDT-SWAP`;

    // 获取当前持仓
    const position = await this.getPosition(symbol);
    if (!position || position.pos === '0') {
      throw new Error('未找到持仓');
    }

    const currentPrice = parseFloat(position.last);
    const posSize = Math.abs(parseFloat(position.pos));

    // 计算止盈止损价格
    let tpPrice = null;
    let slPrice = null;

    if (takeProfit) {
      tpPrice = takeProfit.triggerPrice;
      if (!tpPrice && takeProfit.profitRate) {
        tpPrice = side === 'long'
          ? currentPrice * (1 + takeProfit.profitRate / 100)
          : currentPrice * (1 - takeProfit.profitRate / 100);
      }
    }

    if (stopLoss) {
      slPrice = stopLoss.triggerPrice;
      if (!slPrice && stopLoss.lossRate) {
        slPrice = side === 'long'
          ? currentPrice * (1 - stopLoss.lossRate / 100)
          : currentPrice * (1 + stopLoss.lossRate / 100);
      }
    }

    // 使用OKX的止盈止损订单
    return await this.request('POST', '/trade/order-algo', {
      instId,
      tdMode: 'cross',
      side: side === 'long' ? 'sell' : 'buy',
      ordType: 'conditional',
      sz: posSize.toString(),
      posSide: side,
      ...(tpPrice && { tpTriggerPx: tpPrice.toString(), tpOrdPx: '-1' }),
      ...(slPrice && { slTriggerPx: slPrice.toString(), slOrdPx: '-1' }),
    });
  }

  /**
   * 防守加仓 - 设置条件委托单
   * @param {object} params
   * @param {string} params.symbol - 交易对
   * @param {string} params.side - 方向 ('long', 'short')
   * @param {number} params.anchorPrice - 锚定价格（开仓价）
   * @param {number} params.triggerPercent - 触发百分比（正数=上涨，负数=下跌）
   * @param {number} params.usdtAmount - 加仓USDT数量
   * @param {number} params.leverage - 杠杆倍数
   */
  async setDefenseAddPosition(params) {
    const { symbol, side, anchorPrice, triggerPercent, usdtAmount, leverage } = params;
    const instId = `${symbol}-USDT-SWAP`;
    
    // 计算触发价格：锚定价格 × (1 + 触发百分比/100)
    const triggerPrice = anchorPrice * (1 + triggerPercent / 100);
    
    // 获取合约面值
    const contractSize = await this.getContractSize(symbol);
    
    // 计算下单张数
    const sz = Math.floor((usdtAmount * leverage) / (triggerPrice * contractSize));
    
    if (sz < 1) {
      throw new Error('数量太小，至少需要1张合约');
    }
    
    // 创建条件委托单（trigger类型）
    return await this.request('POST', '/trade/order-algo', {
      instId,
      tdMode: 'cross',  // 全仓模式
      side: side === 'long' ? 'buy' : 'sell',  // 做多=买入，做空=卖出
      ordType: 'trigger',  // 计划委托
      sz: sz.toString(),
      triggerPx: triggerPrice.toFixed(4),  // 触发价格
      orderPx: '-1',  // -1表示市价
      posSide: side,  // 持仓方向
      lever: leverage.toString()
    });
  }

  /**
   * 获取持仓信息
   */
  async getPosition(symbol) {
    const instId = `${symbol}-USDT-SWAP`;
    console.log('🔍 Getting position for:', instId);
    const response = await this.request('GET', `/account/positions?instId=${instId}`);
    console.log('📊 Position response:', JSON.stringify(response, null, 2));
    
    if (response.code !== '0') {
      console.error('❌ OKX API Error:', response.msg);
      throw new Error(`OKX API错误: ${response.msg}`);
    }
    
    const position = response.data?.[0] || null;
    console.log('✅ Position found:', position);
    return position;
  }

  /**
   * 获取所有持仓
   */
  async getAllPositions() {
    const response = await this.request('GET', '/account/positions?instType=SWAP');
    return response.data || [];
  }

  /**
   * 获取计划委托单（包括止盈止损）
   * @param {string} ordType - 订单类型：'conditional'(计划委托), 'oco'(止盈止损), 'trigger'(计划委托)
   * @param {string} state - 订单状态：'live'(生效中), 'effective'(已生效)
   */
  async getAlgoOrders(ordType = 'conditional', state = 'live') {
    const params = new URLSearchParams({
      ordType,
      instType: 'SWAP'
    });
    if (state) {
      params.append('state', state);
    }
    const response = await this.request('GET', `/trade/orders-algo-pending?${params.toString()}`);
    return response.data || [];
  }

  /**
   * 获取指定持仓的止盈止损委托单
   */
  async getTPSLOrders(symbol, side) {
    const instId = `${symbol}-USDT-SWAP`;
    const orders = await this.getAlgoOrders('conditional', 'live');
    return orders.filter(order => 
      order.instId === instId && 
      order.posSide === side &&
      (order.tpTriggerPx || order.slTriggerPx)
    );
  }

  /**
   * 获取所有未成交的委托单
   */
  async getPendingOrders() {
    const response = await this.request('GET', '/trade/orders-pending?instType=SWAP');
    return response.data || [];
  }

  /**
   * 获取ticker数据
   */
  async getTicker(symbol) {
    const instId = `${symbol}-USDT-SWAP`;
    return await this.request('GET', `/market/ticker?instId=${instId}`);
  }

  /**
   * 获取合约面值
   */
  async getContractSize(symbol) {
    const instId = `${symbol}-USDT-SWAP`;
    const response = await this.request('GET', `/public/instruments?instType=SWAP&instId=${instId}`);
    return parseFloat(response.data[0].ctVal);
  }

  /**
   * 计算限价单价格
   */
  calculateLimitPrice(orderBook, side, priceType) {
    const { asks, bids } = orderBook.data[0];
    
    let price;
    switch (priceType) {
      case 'opponent1':
        // 对手价1档：买入用卖1价，卖出用买1价
        price = side === 'buy' ? parseFloat(asks[0][0]) : parseFloat(bids[0][0]);
        break;
      case 'opponent5':
        // 对手价5档：取5档平均价
        const opponentPrices = side === 'buy' 
          ? asks.slice(0, 5).map(a => parseFloat(a[0]))
          : bids.slice(0, 5).map(b => parseFloat(b[0]));
        price = opponentPrices.reduce((a, b) => a + b, 0) / opponentPrices.length;
        break;
      case 'optimal1':
        // 同向价1档：买入用买1价，卖出用卖1价
        price = side === 'buy' ? parseFloat(bids[0][0]) : parseFloat(asks[0][0]);
        break;
      case 'optimal5':
        // 同向价5档：取5档平均价
        const optimalPrices = side === 'buy'
          ? bids.slice(0, 5).map(b => parseFloat(b[0]))
          : asks.slice(0, 5).map(a => parseFloat(a[0]));
        price = optimalPrices.reduce((a, b) => a + b, 0) / optimalPrices.length;
        break;
      default:
        throw new Error(`不支持的价格类型: ${priceType}`);
    }

    return price;
  }

  /**
   * 获取可用USDT余额
   */
  getAvailableUSDT(balance) {
    const usdtBalance = balance.data?.[0]?.details?.find(d => d.ccy === 'USDT');
    return parseFloat(usdtBalance?.availBal || 0);
  }

  /**
   * 撤销订单
   */
  async cancelOrder(symbol, orderId) {
    const instId = `${symbol}-USDT-SWAP`;
    // 尝试使用批量取消API
    return await this.request('POST', '/trade/cancel-batch-orders', [{
      instId,
      ordId: orderId,
    }]);
  }

  /**
   * 撤销算法订单（止盈止损）
   */
  async cancelAlgoOrder(symbol, algoId) {
    const instId = `${symbol}-USDT-SWAP`;
    return await this.request('POST', '/trade/cancel-algos', [{
      instId,
      algoId,
    }]);
  }

  /**
   * 设置持仓模式
   * @param {string} posMode - 持仓模式 ('long_short_mode'=双向持仓, 'net_mode'=单向持仓)
   */
  async setPositionMode(posMode = 'long_short_mode') {
    return await this.request('POST', '/account/set-position-mode', {
      posMode
    });
  }

  /**
   * 获取账户配置
   */
  async getAccountConfig() {
    return await this.request('GET', '/account/config');
  }

  /**
   * 平仓
   */
  async closePosition(symbol, side, size = null) {
    console.log('🔥 closePosition called:', { symbol, side, size });
    
    const position = await this.getPosition(symbol);
    console.log('📊 Position data:', position);
    
    if (!position) {
      throw new Error(`未找到${symbol}的持仓信息`);
    }
    
    const posSize = parseFloat(position.pos || '0');
    if (posSize === 0) {
      throw new Error(`${symbol}持仓数量为0，无需平仓`);
    }

    const closeSize = size || Math.abs(posSize);
    const instId = `${symbol}-USDT-SWAP`;
    
    // 如果没有传side，从position中获取
    const actualSide = side || position.posSide;
    if (!actualSide) {
      throw new Error('无法确定持仓方向');
    }

    console.log('📤 Sending close order:', {
      instId,
      side: actualSide === 'long' ? 'sell' : 'buy',
      sz: closeSize.toString(),
      posSide: actualSide
    });

    return await this.request('POST', '/trade/order', {
      instId,
      tdMode: 'cross',
      side: actualSide === 'long' ? 'sell' : 'buy',
      ordType: 'market',
      sz: closeSize.toString(),
      posSide: actualSide,
      reduceOnly: true,
    });
  }
}

export default OKXTradingAPI;
export { SUPPORTED_SYMBOLS, LEVERAGE_OPTIONS, DEFAULT_LEVERAGE };

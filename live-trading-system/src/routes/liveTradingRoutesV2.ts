/**
 * OKX实盘交易路由 V2 - 多账户版本
 */
import { Hono } from 'hono';
import type { Bindings } from '../types';
import { getOKXAPIByAccount, clearAPICache } from '../utils/okxAPIHelper';

const liveTradingRoutesV2 = new Hono<{ Bindings: Bindings }>();

// ========== 账户管理API ==========

/**
 * 获取所有账户列表
 */
liveTradingRoutesV2.get('/accounts/list', async (c) => {
  try {
    const result = await c.env.DB.prepare(`
      SELECT 
        id, 
        name,
        api_key,
        is_testnet,
        trading_balance,
        funding_balance,
        daily_pnl,
        last_update,
        created_at,
        trade_time
      FROM live_trading_accounts
      ORDER BY created_at DESC
    `).all();

    return c.json({
      success: true,
      accounts: result.results || []
    });
  } catch (error: any) {
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 添加新账户
 */
liveTradingRoutesV2.post('/accounts/add', async (c) => {
  try {
    const body = await c.req.json();
    const { accountName, apiKey, apiSecret, passphrase, isTestnet } = body;

    if (!accountName || !apiKey || !apiSecret || !passphrase) {
      return c.json({
        success: false,
        error: '缺少必要参数'
      }, 400);
    }

    // 尝试获取账户余额作为初始余额
    let initialBalance = 0;
    try {
      const api = new OKXTradingAPI(apiKey, apiSecret, passphrase, isTestnet);
      const balance = await api.getBalance();
      const usdtData = balance.data?.[0]?.details?.find((d: any) => d.ccy === 'USDT');
      initialBalance = parseFloat(usdtData?.availBal || '0');
    } catch (err) {
      console.log('无法获取初始余额，将设为0');
    }
    
    // 生成账户ID
    const accountId = `acc_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    // 插入新账户
    const result = await c.env.DB.prepare(`
      INSERT INTO live_trading_accounts (
        id, name, api_key, secret_key, passphrase, is_testnet, initial_balance, created_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `).bind(accountId, accountName, apiKey, apiSecret, passphrase, isTestnet ? 1 : 0, initialBalance, new Date().toISOString()).run();

    return c.json({
      success: true,
      accountId: accountId,
      message: '账户添加成功'
    });
  } catch (error: any) {
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 删除账户
 */
liveTradingRoutesV2.delete('/accounts/:id', async (c) => {
  try {
    const accountId = c.req.param('id'); // ID is string, not integer

    // 先删除所有关联数据（按依赖顺序）- 使用try-catch忽略不存在的表
    try { await c.env.DB.prepare(`DELETE FROM defense_add_config WHERE account_id = ?`).bind(accountId).run(); } catch(e) {}
    try { await c.env.DB.prepare(`DELETE FROM position_tpsl_config WHERE account_id = ?`).bind(accountId).run(); } catch(e) {}
    try { await c.env.DB.prepare(`DELETE FROM live_orders WHERE account_id = ?`).bind(accountId).run(); } catch(e) {}
    try { await c.env.DB.prepare(`DELETE FROM live_trading_configs WHERE account_id = ?`).bind(accountId).run(); } catch(e) {}
    try { await c.env.DB.prepare(`DELETE FROM trade_history WHERE account_id = ?`).bind(accountId).run(); } catch(e) {}
    
    // 最后删除账户
    await c.env.DB.prepare(`DELETE FROM live_trading_accounts WHERE id = ?`).bind(accountId).run();

    // 清除API缓存
    clearAPICache(accountId);

    return c.json({ success: true, message: '账户已删除' });
  } catch (error: any) {
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 测试账户连接
 */
liveTradingRoutesV2.get('/accounts/:id/test', async (c) => {
  try {
    const accountId = c.req.param('id');  // Keep as string
    
    // 清除该账户的缓存，强制重新创建
    clearAPICache(accountId);
    
    const api = await getOKXAPIByAccount(c.env.DB, accountId);
    const balance = await api.getBalance();
    
    const usdtData = balance.data?.[0]?.details?.find((d: any) => d.ccy === 'USDT');
    const balanceAmount = parseFloat(usdtData?.availBal || '0');

    return c.json({
      success: true,
      balance: balanceAmount.toFixed(2)
    });
  } catch (error: any) {
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 更新账户初始余额
 */
liveTradingRoutesV2.put('/accounts/:id/initial-balance', async (c) => {
  try {
    const accountId = c.req.param('id');
    const body = await c.req.json();
    const { initialBalance } = body;
    
    if (typeof initialBalance !== 'number' || initialBalance < 0) {
      return c.json({
        success: false,
        error: '初始余额必须是非负数'
      }, 400);
    }
    
    await c.env.DB.prepare(`
      UPDATE live_trading_accounts 
      SET initial_balance = ?
      WHERE id = ?
    `).bind(initialBalance, accountId).run();
    
    return c.json({ 
      success: true,
      message: '初始余额已更新'
    });
  } catch (error: any) {
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 获取账户配置详情
 */
liveTradingRoutesV2.get('/accounts/:id/config', async (c) => {
  try {
    const accountId = c.req.param('id');
    
    const api = await getOKXAPIByAccount(c.env.DB, accountId);
    const config = await api.getAccountConfig();
    
    return c.json({
      success: true,
      config: config.data?.[0] || {}
    });
  } catch (error: any) {
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 测试API连接（不保存）
 */
liveTradingRoutesV2.post('/test-connection', async (c) => {
  try {
    const body = await c.req.json();
    const { apiKey, apiSecret, passphrase, isTestnet } = body;

    const api = new OKXTradingAPI(apiKey, apiSecret, passphrase, isTestnet);
    const balance = await api.getBalance();
    
    const usdtData = balance.data?.[0]?.details?.find((d: any) => d.ccy === 'USDT');
    const balanceAmount = parseFloat(usdtData?.availBal || '0');

    return c.json({
      success: true,
      balance: balanceAmount.toFixed(2)
    });
  } catch (error: any) {
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

// ========== 交易API（多账户版本） ==========

/**
 * 获取账户信息
 */
liveTradingRoutesV2.get('/account', async (c) => {
  try {
    const accountId = c.req.query('accountId') || '';
    if (!accountId) {
      return c.json({ success: false, error: '缺少accountId参数' }, 400);
    }

    const api = await getOKXAPIByAccount(c.env.DB, accountId);
    
    // 获取余额信息
    const balance = await api.getBalance();
    const usdtData = balance.data?.[0]?.details?.find((d: any) => d.ccy === 'USDT');
    
    // 获取所有持仓，计算实时未实现盈亏
    const positions = await api.getAllPositions();
    let totalUnrealizedPnl = 0;
    
    if (positions && positions.length > 0) {
      for (const pos of positions) {
        // OKX API返回的upl字段就是该持仓的未实现盈亏
        const posUpl = parseFloat(pos.upl || '0');
        totalUnrealizedPnl += posUpl;
      }
    }
    
    // 获取账户配置的初始金额
    const configResult = await c.env.DB.prepare(`
      SELECT initial_balance, DATE(created_at) as start_date FROM live_trading_accounts WHERE id = ?
    `).bind(accountId).first();
    
    const initialBalance = parseFloat(configResult?.initial_balance || '0');
    
    // 获取当日交易盈亏（从trade_history表）
    const today = new Date().toISOString().split('T')[0];
    const dailyPnlResult = await c.env.DB.prepare(`
      SELECT COALESCE(SUM(pnl), 0) as daily_pnl 
      FROM trade_history 
      WHERE account_id = ? AND DATE(trade_time) = ?
    `).bind(accountId, today).first();
    
    const dailyPnl = parseFloat(dailyPnlResult?.daily_pnl || '0');
    
    return c.json({
      success: true,
      account: {
        totalEquity: parseFloat(usdtData?.eq || '0'),
        availableBalance: parseFloat(usdtData?.availBal || '0'),
        unrealizedPnl: totalUnrealizedPnl,  // 使用从持仓计算的实时未实现盈亏
        realizedPnl: 0,
        initialBalance,
        dailyPnl
      }
    });
  } catch (error: any) {
    console.error('获取账户信息失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 获取Ticker行情
 */
liveTradingRoutesV2.get('/ticker/:symbol', async (c) => {
  try {
    const symbol = c.req.param('symbol');
    const accountId = c.req.query('accountId') || '';
    
    if (!accountId) {
      return c.json({ success: false, error: '缺少accountId参数' }, 400);
    }

    const api = await getOKXAPIByAccount(c.env.DB, accountId);
    const ticker = await api.getTicker(symbol);
    
    if (ticker.code === '0' && ticker.data && ticker.data.length > 0) {
      const data = ticker.data[0];
      return c.json({
        success: true,
        ticker: {
          last: data.last,
          changePercent: ((parseFloat(data.last) - parseFloat(data.open24h)) / parseFloat(data.open24h) * 100).toFixed(2)
        }
      });
    }

    return c.json({ success: false, error: '无法获取行情数据' });
  } catch (error: any) {
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 限价委托下单
 */
liveTradingRoutesV2.post('/order/limit', async (c) => {
  try {
    const body = await c.req.json();
    const { accountId, symbol, side, priceType, leverage, usdtAmount, customPrice } = body;
    
    // 调试日志
    console.log('接收到的订单数据:', JSON.stringify(body, null, 2));
    console.log('priceType值:', priceType, '类型:', typeof priceType);

    if (!accountId || !symbol || !side || !leverage || !usdtAmount) {
      return c.json({
        success: false,
        error: '缺少必要参数'
      }, 400);
    }
    
    // 验证价格参数
    if (!priceType || (priceType === 'custom' && !customPrice)) {
      return c.json({
        success: false,
        error: '请选择价格类型或输入自定义价格'
      }, 400);
    }

    const api = await getOKXAPIByAccount(c.env.DB, accountId);
    
    // 检查账户模式
    const accountConfig = await api.getAccountConfig();
    const acctLv = accountConfig.data?.[0]?.acctLv;
    
    if (acctLv === '1') {
      return c.json({
        success: false,
        error: '账户当前处于简单交易模式，无法进行合约交易。\n\n请按以下步骤操作：\n1. 登录OKX官网 (www.okx.com)\n2. 进入"资产" → "账户设置" → "账户模式"\n3. 切换到"单向交易模式"或更高级模式\n4. 等待切换完成后，返回此页面重新下单\n\n注意：切换账户模式需要在账户无持仓和挂单的情况下进行。'
      }, 400);
    }
    
    // 构建订单参数
    const orderParams: any = {
      symbol,
      side,
      leverage,
      usdtAmount
    };
    
    // 如果是自定义价格，使用price字段；否则使用priceType
    if (priceType === 'custom') {
      orderParams.price = parseFloat(customPrice);
    } else {
      orderParams.priceType = priceType;
    }
    
    const result = await api.limitOrder(orderParams);

    console.log('OKX订单返回结果:', JSON.stringify(result, null, 2));

    // 保存订单记录
    if (result.code === '0') {
      const orderData = result.data[0];
      const orderId = orderData.ordId;
      // OKX返回的sz字段在下单时可能不存在，使用计算值或设为0
      const orderSize = parseFloat(orderData.sz || orderData.fillSz || '0');
      const orderPrice = parseFloat(orderData.px || orderData.avgPx || '0');
      
      await c.env.DB.prepare(`
        INSERT INTO live_orders (
          account_id, symbol, side, order_type, price_type, price, size, usdt_amount, leverage, 
          okx_order_id, status, created_at
        ) VALUES (?, ?, ?, 'limit', ?, ?, ?, ?, ?, ?, 'pending', datetime('now'))
      `).bind(accountId, symbol, side, priceType, orderPrice, orderSize, usdtAmount, leverage, orderId).run();
    }

    return c.json({
      success: result.code === '0',
      data: result.data,
      error: result.msg
    });
  } catch (error: any) {
    console.error('限价委托失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 市价委托下单
 */
liveTradingRoutesV2.post('/order/market', async (c) => {
  try {
    const body = await c.req.json();
    const { accountId, symbol, side, leverage, usdtAmount, takeProfitRate, stopLossRate } = body;

    if (!accountId || !symbol || !side || !leverage || !usdtAmount) {
      return c.json({
        success: false,
        error: '缺少必要参数'
      }, 400);
    }

    const api = await getOKXAPIByAccount(c.env.DB, accountId);
    
    // 检查账户模式
    const accountConfig = await api.getAccountConfig();
    const acctLv = accountConfig.data?.[0]?.acctLv;
    
    if (acctLv === '1') {
      return c.json({
        success: false,
        error: '账户当前处于简单交易模式，无法进行合约交易。\n\n请按以下步骤操作：\n1. 登录OKX官网 (www.okx.com)\n2. 进入"资产" → "账户设置" → "账户模式"\n3. 切换到"单向交易模式"或更高级模式\n4. 等待切换完成后，返回此页面重新下单\n\n注意：切换账户模式需要在账户无持仓和挂单的情况下进行。'
      }, 400);
    }
    
    const result = await api.marketOrder({
      symbol,
      side,
      leverage,
      usdtAmount
    });

    // 保存订单记录
    if (result.code === '0') {
      const orderData = result.data[0];
      const orderId = orderData.ordId;
      const orderSize = parseFloat(orderData.sz || '0');
      
      await c.env.DB.prepare(`
        INSERT INTO live_orders (
          account_id, symbol, side, order_type, size, usdt_amount, leverage, 
          okx_order_id, status, created_at
        ) VALUES (?, ?, ?, 'market', ?, ?, ?, ?, 'pending', datetime('now'))
      `).bind(accountId, symbol, side, orderSize, usdtAmount, leverage, orderId).run();
      
      // 🆕 自动设置止盈止损到OKX
      if (takeProfitRate || stopLossRate) {
        try {
          // 等待1.5秒让持仓数据在OKX更新
          await new Promise(resolve => setTimeout(resolve, 1500));
          
          const tpslParams: any = {
            symbol,
            side
          };
          
          if (takeProfitRate) {
            tpslParams.takeProfit = {
              profitRate: takeProfitRate
            };
          }
          
          if (stopLossRate) {
            tpslParams.stopLoss = {
              lossRate: Math.abs(stopLossRate)
            };
          }
          
          const tpslResult = await api.setFullTPSL(tpslParams);
          console.log('✅ 已自动设置OKX止盈止损:', tpslResult);
          
          // 返回包含止盈止损信息的成功响应
          return c.json({
            success: true,
            data: result.data,
            tpslSet: true,
            tpslResult: tpslResult,
            message: '下单成功，止盈止损已设置'
          });
          
        } catch (tpslError: any) {
          console.error('❌ 设置止盈止损失败:', tpslError.message);
          // 不影响主流程，返回警告
          return c.json({
            success: true,
            data: result.data,
            tpslSet: false,
            warning: `下单成功，但止盈止损设置失败: ${tpslError.message}`
          });
        }
      }
    }

    // 检查OKX响应
    console.log('📊 OKX市价单响应:', JSON.stringify(result, null, 2));
    
    if (result.code !== '0') {
      console.error('❌ OKX返回错误:', result.msg, '数据:', result.data);
      return c.json({
        success: false,
        error: `OKX错误: ${result.msg || '未知错误'}`,
        okxCode: result.code,
        details: result.data
      }, 400);
    }
    
    return c.json({
      success: true,
      data: result.data,
      message: '下单成功'
    });
  } catch (error: any) {
    console.error('❌ 市价委托异常:', error);
    console.error('❌ 错误堆栈:', error.stack);
    
    // 提取更详细的错误信息
    let errorMessage = error.message;
    if (error.response && error.response.data) {
      const okxError = error.response.data;
      errorMessage = `OKX API错误: ${okxError.msg || okxError.error_message || error.message}`;
      console.error('❌ OKX响应错误:', JSON.stringify(okxError, null, 2));
    }
    
    return c.json({
      success: false,
      error: errorMessage
    }, 500);
  }
});

/**
 * 获取持仓
 */
liveTradingRoutesV2.get('/positions', async (c) => {
  try {
    const accountId = c.req.query('accountId') || '';
    if (!accountId) {
      return c.json({ success: false, error: '缺少accountId参数' }, 400);
    }

    const api = await getOKXAPIByAccount(c.env.DB, accountId);
    const positions = await api.getAllPositions();

    // 过滤并格式化持仓
    const activePositions = await Promise.all(
      positions
        .filter((pos: any) => parseFloat(pos.pos) !== 0)
        .map(async (pos: any) => {
          const entryPrice = parseFloat(pos.avgPx);
          const currentPrice = parseFloat(pos.last);
          const pnl = parseFloat(pos.upl);
          const leverage = parseInt(pos.lever);
          
          // 计算收益率：价格变动百分比 × 杠杆倍数
          const priceChangeRate = ((currentPrice - entryPrice) / entryPrice) * 100;
          const pnlRate = priceChangeRate * leverage * (pos.posSide === 'long' ? 1 : -1);

          // 🔧 修复：使用OKX返回的实际保证金金额
          // imr = 初始保证金（实际投入的USDT）
          // margin = 保证金占用（含盈亏）
          const usdtAmount = parseFloat(pos.imr) || parseFloat(pos.margin) || 0;
          
          // 查询该持仓的止盈止损配置
          const tpslConfig = await c.env.DB.prepare(`
            SELECT 
              take_profit_price, take_profit_rate,
              stop_loss_price, stop_loss_rate,
              max_hold_timeframe, max_hold_bars
            FROM position_tpsl_config
            WHERE position_id = ? AND is_active = 1
            LIMIT 1
          `).bind(pos.posId).first();
          
          return {
            id: pos.posId,
            symbol: pos.instId.split('-')[0],
            side: pos.posSide,
            entryPrice,
            currentPrice,
            size: Math.abs(parseFloat(pos.pos)),
            leverage: parseInt(pos.lever),
            usdtAmount: usdtAmount || 0,
            pnl,
            pnlRate,
            // 附加止盈止损配置（如果存在）
            tpslConfig: tpslConfig ? {
              takeProfitPrice: tpslConfig.take_profit_price,
              takeProfitRate: tpslConfig.take_profit_rate,
              stopLossPrice: tpslConfig.stop_loss_price,
              stopLossRate: tpslConfig.stop_loss_rate,
              maxHoldTimeframe: tpslConfig.max_hold_timeframe,
              maxHoldBars: tpslConfig.max_hold_bars
            } : null
          };
        })
    );

    return c.json({
      success: true,
      positions: activePositions
    });
  } catch (error: any) {
    console.error('获取持仓失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 平仓（支持百分比平仓）
 */
liveTradingRoutesV2.post('/position/:id/close', async (c) => {
  try {
    const positionId = c.req.param('id');
    const accountId = c.req.query('accountId') || '';
    const percentage = parseInt(c.req.query('percentage') || '100'); // 平仓百分比：30, 50, 100
    
    if (!accountId) {
      return c.json({ success: false, error: '缺少accountId参数' }, 400);
    }

    if (percentage <= 0 || percentage > 100) {
      return c.json({ success: false, error: '平仓百分比必须在1-100之间' }, 400);
    }

    const api = await getOKXAPIByAccount(c.env.DB, accountId);
    const positions = await api.getAllPositions();
    
    const position = positions.find((pos: any) => pos.posId === positionId);

    if (!position) {
      return c.json({
        success: false,
        error: '未找到持仓'
      }, 404);
    }

    // 从 instId 提取 symbol
    const symbol = position.instId.split('-')[0];
    const actualSide = position.posSide;
    
    // 计算平仓数量
    const totalSize = Math.abs(parseFloat(position.pos));
    
    if (totalSize === 0) {
      return c.json({
        success: false,
        error: `${symbol}持仓数量为0，无需平仓`
      }, 400);
    }
    
    const closeSize = percentage === 100 ? totalSize : Math.floor(totalSize * percentage / 100);
    const instId = position.instId;

    let result;
    
    // 如果是100%平仓，使用一键平仓API（更快更可靠）
    if (percentage === 100) {
      result = await api.request('POST', '/trade/close-position', {
        instId,
        mgnMode: 'cross',
        posSide: actualSide,
      });
      
      // 如果一键平仓失败，使用市价单
      if (result.code !== '0') {
        console.log('一键平仓失败，尝试市价单:', result.msg);
        result = await api.request('POST', '/trade/order', {
          instId,
          tdMode: 'cross',
          side: actualSide === 'long' ? 'sell' : 'buy',
          ordType: 'market',
          sz: closeSize.toString(),
          posSide: actualSide,
          reduceOnly: true,
        });
      }
    } else {
      // 部分平仓，必须使用市价单
      console.log(`部分平仓 ${percentage}%: totalSize=${totalSize}, closeSize=${closeSize}`);
      result = await api.request('POST', '/trade/order', {
        instId,
        tdMode: 'cross',
        side: actualSide === 'long' ? 'sell' : 'buy',
        ordType: 'market',
        sz: closeSize.toString(),
        posSide: actualSide,
        reduceOnly: true,
      });
    }

    return c.json({
      success: result.code === '0',
      data: result.data,
      error: result.msg,
      info: {
        percentage,
        totalSize,
        closeSize: closeSize || totalSize
      }
    });
  } catch (error: any) {
    console.error('平仓失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 设置止盈止损
 */
liveTradingRoutesV2.post('/position/set-tpsl', async (c) => {
  try {
    const body = await c.req.json();
    const { accountId, positionId, symbol, side, takeProfit, stopLoss, maxHold } = body;

    if (!accountId || !positionId || !symbol || !side) {
      return c.json({
        success: false,
        error: '缺少必要参数'
      }, 400);
    }

    const api = await getOKXAPIByAccount(c.env.DB, accountId);
    
    // 保存止盈止损配置到数据库
    // 注意：这里先保存配置，实际的止盈止损触发需要一个监控服务

    // 检查是否已有配置
    const existing = await c.env.DB.prepare(`
      SELECT id FROM position_tpsl_config 
      WHERE position_id = ? AND is_active = 1
    `).bind(positionId).first();

    if (existing) {
      // 更新现有配置
      await c.env.DB.prepare(`
        UPDATE position_tpsl_config 
        SET take_profit_price = ?, take_profit_rate = ?,
            stop_loss_price = ?, stop_loss_rate = ?,
            max_hold_timeframe = ?, max_hold_bars = ?,
            updated_at = datetime('now')
        WHERE id = ?
      `).bind(
        takeProfit?.price || null,
        takeProfit?.rate || null,
        stopLoss?.price || null,
        stopLoss?.rate || null,
        maxHold?.timeframe || null,
        maxHold?.bars || null,
        existing.id
      ).run();
    } else {
      // 插入新配置
      await c.env.DB.prepare(`
        INSERT INTO position_tpsl_config (
          position_id, account_id, symbol, side,
          take_profit_price, take_profit_rate,
          stop_loss_price, stop_loss_rate,
          max_hold_timeframe, max_hold_bars,
          is_active, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))
      `).bind(
        positionId,
        accountId,
        symbol,
        side,
        takeProfit?.price || null,
        takeProfit?.rate || null,
        stopLoss?.price || null,
        stopLoss?.rate || null,
        maxHold?.timeframe || null,
        maxHold?.bars || null
      ).run();
    }

    // 如果设置了止盈止损，在OKX设置实际的止盈止损委托单
    if ((takeProfit?.price || takeProfit?.rate) || (stopLoss?.price || stopLoss?.rate)) {
      try {
        const tpslParams: any = {
          symbol,
          side
        };
        
        if (takeProfit?.price || takeProfit?.rate) {
          tpslParams.takeProfit = {
            triggerPrice: takeProfit.price,
            profitRate: takeProfit.rate
          };
        }
        
        if (stopLoss?.price || stopLoss?.rate) {
          tpslParams.stopLoss = {
            triggerPrice: stopLoss.price,
            lossRate: stopLoss.rate ? Math.abs(stopLoss.rate) : null
          };
        }
        
        // 调用OKX API设置止盈止损
        const result = await api.setFullTPSL(tpslParams);
        console.log('OKX止盈止损设置成功:', result);
        
        return c.json({
          success: true,
          message: '止盈止损配置已保存并在OKX生效',
          okxResult: result
        });
      } catch (error: any) {
        console.error('设置OKX止盈止损失败:', error);
        return c.json({
          success: false,
          error: `止盈止损配置已保存，但OKX设置失败: ${error.message}`
        }, 500);
      }
    }

    return c.json({
      success: true,
      message: '止盈止损配置已保存'
    });
  } catch (error: any) {
    console.error('设置止盈止损失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 检查止盈止损状态
 */
liveTradingRoutesV2.get('/position/:id/tpsl-status', async (c) => {
  try {
    const positionId = c.req.param('id');
    const accountId = c.req.query('accountId') || '';
    
    if (!accountId) {
      return c.json({ success: false, error: '缺少accountId参数' }, 400);
    }

    const api = await getOKXAPIByAccount(c.env.DB, accountId);
    
    // 获取该持仓的配置
    const config = await c.env.DB.prepare(`
      SELECT * FROM position_tpsl_config
      WHERE position_id = ? AND is_active = 1
      LIMIT 1
    `).bind(positionId).first();

    if (!config) {
      return c.json({
        success: true,
        hasConfig: false,
        message: '未设置止盈止损'
      });
    }

    // 获取持仓信息
    const positions = await api.getAllPositions();
    const position = positions.find((pos: any) => pos.posId === positionId);
    
    if (!position) {
      return c.json({
        success: false,
        error: '未找到持仓'
      }, 404);
    }

    const symbol = position.instId.split('-')[0];
    const side = position.posSide;

    // 查询OKX的止盈止损委托单
    const tpslOrders = await api.getTPSLOrders(symbol, side);

    // 计算最大持有周期进度
    let holdingProgress = null;
    if (config.max_hold_timeframe && config.max_hold_bars) {
      const createdAt = new Date(config.created_at).getTime();
      const now = Date.now();
      const elapsedMs = now - createdAt;
      
      // 计算周期时长（毫秒）
      const timeframeMs: { [key: string]: number } = {
        '1m': 60 * 1000,
        '5m': 5 * 60 * 1000,
        '15m': 15 * 60 * 1000,
        '1h': 60 * 60 * 1000,
        '4h': 4 * 60 * 60 * 1000,
        '1d': 24 * 60 * 60 * 1000
      };
      
      const barDuration = timeframeMs[config.max_hold_timeframe] || timeframeMs['5m'];
      const totalDuration = barDuration * config.max_hold_bars;
      const elapsedBars = Math.floor(elapsedMs / barDuration);
      const remainingBars = Math.max(0, config.max_hold_bars - elapsedBars);
      const progressPercent = Math.min(100, (elapsedMs / totalDuration) * 100);
      
      holdingProgress = {
        timeframe: config.max_hold_timeframe,
        maxBars: config.max_hold_bars,
        elapsedBars,
        remainingBars,
        progressPercent: progressPercent.toFixed(1),
        createdAt: config.created_at,
        willCloseAt: new Date(createdAt + totalDuration).toISOString()
      };
    }

    return c.json({
      success: true,
      hasConfig: true,
      config: {
        takeProfitPrice: config.take_profit_price,
        takeProfitRate: config.take_profit_rate,
        stopLossPrice: config.stop_loss_price,
        stopLossRate: config.stop_loss_rate,
        maxHoldTimeframe: config.max_hold_timeframe,
        maxHoldBars: config.max_hold_bars,
        createdAt: config.created_at
      },
      okxOrders: tpslOrders.map((order: any) => ({
        orderId: order.algoId,
        state: order.state,
        tpTriggerPrice: order.tpTriggerPx,
        slTriggerPrice: order.slTriggerPx,
        createTime: order.cTime
      })),
      holdingProgress,
      message: tpslOrders.length > 0 ? '止盈止损已在OKX生效' : '⚠️ 未找到OKX委托单，可能未生效'
    });
  } catch (error: any) {
    console.error('检查止盈止损状态失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 获取防守加仓列表
 */
liveTradingRoutesV2.get('/position/:id/defense-list', async (c) => {
  try {
    const positionId = c.req.param('id');
    const accountId = c.req.query('accountId') || '';
    
    if (!accountId) {
      return c.json({ success: false, error: '缺少accountId参数' }, 400);
    }

    // 查询该持仓的所有防守单
    const defenseList = await c.env.DB.prepare(`
      SELECT * FROM defense_add_config
      WHERE position_id = ? AND account_id = ? AND status = 'active'
      ORDER BY created_at DESC
    `).bind(positionId, accountId).all();

    // 获取OKX的委托单状态
    const api = await getOKXAPIByAccount(c.env.DB, accountId);
    const okxOrders = await api.getAlgoOrders('trigger', 'live');
    
    // 只返回在OKX中确实存在的防守单（过滤掉unknown状态的）
    const defenseOrders = defenseList.results
      .map((defense: any) => {
        const okxOrder = okxOrders.find((order: any) => 
          order.algoId === defense.okx_order_id
        );
        
        const triggerPrice = defense.anchor_price * (1 + defense.trigger_percent / 100);
        const direction = defense.trigger_percent < 0 ? '下跌' : '上涨';
        
        return {
          id: defense.id,
          symbol: defense.symbol,
          side: defense.side,
          anchorPrice: defense.anchor_price,
          triggerPercent: defense.trigger_percent,
          triggerPrice: triggerPrice.toFixed(4),
          direction,
          usdtAmount: defense.usdt_amount,
          leverage: defense.leverage,
          okxOrderId: defense.okx_order_id,
          okxStatus: okxOrder ? okxOrder.state : null,
          okxOrder: okxOrder,
          createdAt: defense.created_at
        };
      })
      .filter((defense: any) => {
        // 只保留在OKX中确实存在且状态为live的订单
        return defense.okxOrder && defense.okxStatus === 'live';
      })
      .map((defense: any) => {
        // 移除okxOrder字段，只保留必要信息
        const { okxOrder, ...rest } = defense;
        return { ...rest, okxStatus: 'live' };
      });

    return c.json({
      success: true,
      orders: defenseOrders
    });
  } catch (error: any) {
    console.error('获取防守单列表失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 清理数据库中已失效的防守单（OKX中不存在的）
 * POST /defense/cleanup
 */
liveTradingRoutesV2.post('/defense/cleanup', async (c) => {
  try {
    const accountId = c.req.query('accountId') || '';
    if (!accountId) {
      return c.json({ success: false, error: '缺少accountId参数' }, 400);
    }

    const api = await getOKXAPIByAccount(c.env.DB, accountId);
    
    // 获取OKX中所有活跃的算法委托单
    const okxOrders = await api.getAlgoOrders('trigger', 'live');
    const okxOrderIds = new Set(okxOrders.map((order: any) => order.algoId));
    
    // 查询数据库中所有状态为active的防守单
    const defenseList = await c.env.DB.prepare(`
      SELECT * FROM defense_add_config
      WHERE account_id = ? AND status = 'active'
    `).bind(accountId).all();

    let cleanedCount = 0;

    // 将不在OKX中的防守单标记为cancelled
    for (const defense of defenseList.results || []) {
      if (!okxOrderIds.has(defense.okx_order_id)) {
        await c.env.DB.prepare(`
          UPDATE defense_add_config 
          SET status = 'cancelled', updated_at = datetime('now')
          WHERE id = ?
        `).bind(defense.id).run();
        cleanedCount++;
      }
    }

    return c.json({
      success: true,
      cleanedCount,
      message: `已清理 ${cleanedCount} 个失效的防守单记录`
    });
  } catch (error: any) {
    console.error('清理失效防守单失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 清除所有防守单
 * DELETE /defense/clear-all
 */
liveTradingRoutesV2.delete('/defense/clear-all', async (c) => {
  try {
    const accountId = c.req.query('accountId') || '';
    if (!accountId) {
      return c.json({ success: false, error: '缺少accountId参数' }, 400);
    }

    const api = await getOKXAPIByAccount(c.env.DB, accountId);
    
    // 查询该账户的所有活动防守单
    const defenseList = await c.env.DB.prepare(`
      SELECT * FROM defense_add_config
      WHERE account_id = ? AND status = 'active'
    `).bind(accountId).all();

    if (!defenseList.results || defenseList.results.length === 0) {
      return c.json({
        success: true,
        canceledCount: 0,
        message: '没有防守单需要清除'
      });
    }

    let canceledCount = 0;
    const errors: string[] = [];

    // 批量取消OKX的委托单并更新数据库
    for (const defense of defenseList.results) {
      try {
        // 取消OKX委托单
        if (defense.okx_order_id) {
          try {
            await api.request('POST', '/trade/cancel-algos', [{
              algoId: defense.okx_order_id,
              instId: `${defense.symbol}-USDT-SWAP`
            }]);
          } catch (error) {
            console.error(`取消OKX委托单失败 ${defense.okx_order_id}:`, error);
            // 即使OKX取消失败，也继续更新数据库状态
          }
        }

        // 更新数据库状态
        await c.env.DB.prepare(`
          UPDATE defense_add_config 
          SET status = 'cancelled', updated_at = datetime('now')
          WHERE id = ?
        `).bind(defense.id).run();

        canceledCount++;
      } catch (error: any) {
        errors.push(`防守单 ${defense.id}: ${error.message}`);
      }
    }

    return c.json({
      success: canceledCount > 0,
      canceledCount,
      totalDefenseOrders: defenseList.results.length,
      errors: errors.length > 0 ? errors : undefined,
      message: `成功清除 ${canceledCount}/${defenseList.results.length} 个防守单`
    });
  } catch (error: any) {
    console.error('清除所有防守单失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 取消防守加仓
 */
liveTradingRoutesV2.delete('/defense/:id', async (c) => {
  try {
    const defenseId = c.req.param('id');
    const accountId = c.req.query('accountId') || '';
    
    if (!accountId) {
      return c.json({ success: false, error: '缺少accountId参数' }, 400);
    }

    // 查询防守单
    const defense = await c.env.DB.prepare(`
      SELECT * FROM defense_add_config WHERE id = ? AND account_id = ?
    `).bind(defenseId, accountId).first();

    if (!defense) {
      return c.json({ success: false, error: '未找到防守单' }, 404);
    }

    // 取消OKX委托单
    if (defense.okx_order_id) {
      const api = await getOKXAPIByAccount(c.env.DB, accountId);
      try {
        await api.request('POST', '/trade/cancel-algos', [{
          algoId: defense.okx_order_id,
          instId: `${defense.symbol}-USDT-SWAP`
        }]);
      } catch (error) {
        console.error('取消OKX委托单失败:', error);
      }
    }

    // 更新数据库状态
    await c.env.DB.prepare(`
      UPDATE defense_add_config 
      SET status = 'cancelled', updated_at = datetime('now')
      WHERE id = ?
    `).bind(defenseId).run();

    return c.json({
      success: true,
      message: '防守单已取消'
    });
  } catch (error: any) {
    console.error('取消防守单失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 设置防守加仓
 */
liveTradingRoutesV2.post('/position/defense-add', async (c) => {
  try {
    const body = await c.req.json();
    const { accountId, positionId, symbol, side, anchorPrice, triggerPercent, usdtAmount, leverage } = body;

    if (!accountId || !symbol || !side || !anchorPrice || !triggerPercent || !usdtAmount || !leverage) {
      return c.json({
        success: false,
        error: '缺少必要参数'
      }, 400);
    }

    const api = await getOKXAPIByAccount(c.env.DB, accountId);
    
    // 调用OKX API设置防守加仓条件单
    const result = await api.setDefenseAddPosition({
      symbol,
      side,
      anchorPrice: parseFloat(anchorPrice),
      triggerPercent: parseFloat(triggerPercent),
      usdtAmount: parseFloat(usdtAmount),
      leverage: parseInt(leverage)
    });

    // 保存配置到数据库
    await c.env.DB.prepare(`
      INSERT INTO defense_add_config (
        position_id, account_id, symbol, side,
        anchor_price, trigger_percent, usdt_amount, leverage,
        okx_order_id, created_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    `).bind(
      positionId,
      accountId,
      symbol,
      side,
      anchorPrice,
      triggerPercent,
      usdtAmount,
      leverage,
      result.data?.[0]?.algoId || null
    ).run();

    return c.json({
      success: true,
      message: '防守加仓设置成功',
      okxResult: result
    });
  } catch (error: any) {
    console.error('设置防守加仓失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 获取交易历史记录
 * GET /trade-history
 */
liveTradingRoutesV2.get('/trade-history', async (c) => {
  try {
    const accountId = c.req.query('accountId');
    const symbol = c.req.query('symbol');
    const limit = parseInt(c.req.query('limit') || '100');
    const startDate = c.req.query('startDate');
    const endDate = c.req.query('endDate');
    
    if (!accountId) {
      return c.json({ success: false, error: '缺少账户ID' }, 400);
    }
    
    let query = `
      SELECT * FROM trade_history 
      WHERE account_id = ?
    `;
    const params: any[] = [accountId];
    
    if (symbol) {
      query += ` AND symbol = ?`;
      params.push(symbol);
    }
    
    if (startDate) {
      query += ` AND trade_time >= ?`;
      params.push(startDate);
    }
    
    if (endDate) {
      query += ` AND trade_time <= ?`;
      params.push(endDate);
    }
    
    query += ` ORDER BY trade_time DESC LIMIT ?`;
    params.push(limit);
    
    const result = await c.env.DB.prepare(query).bind(...params).all();
    
    // Format trades for frontend with Beijing time
    const formattedTrades = (result.results || []).map((trade: any) => {
      const tradeTime = new Date(trade.trade_time);
      return {
        ...trade,
        trade_time_beijing: tradeTime.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
      };
    });
    
    return c.json({
      success: true,
      total: result.results?.length || 0,
      data: formattedTrades  // Changed from 'trades' to 'data' to match frontend expectation
    });
  } catch (error: any) {
    console.error('获取交易历史失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 导出交易历史为CSV
 * GET /trade-history/export
 */
liveTradingRoutesV2.get('/trade-history/export', async (c) => {
  try {
    const accountId = c.req.query('accountId');
    const symbol = c.req.query('symbol');
    const startDate = c.req.query('startDate');
    const endDate = c.req.query('endDate');
    
    if (!accountId) {
      return c.json({ success: false, error: '缺少账户ID' }, 400);
    }
    
    let query = `
      SELECT * FROM trade_history 
      WHERE account_id = ?
    `;
    const params: any[] = [accountId];
    
    if (symbol) {
      query += ` AND symbol = ?`;
      params.push(symbol);
    }
    
    if (startDate) {
      query += ` AND trade_time >= ?`;
      params.push(startDate);
    }
    
    if (endDate) {
      query += ` AND trade_time <= ?`;
      params.push(endDate);
    }
    
    query += ` ORDER BY trade_time DESC`;
    
    const result = await c.env.DB.prepare(query).bind(...params).all();
    const trades = result.results || [];
    
    // 生成CSV内容
    const headers = [
      'ID', '交易时间', '币种', '交易类型', '方向', '订单类型', 
      '价格', '数量', 'USDT金额', '杠杆', '手续费', '盈亏', '盈亏率(%)', 
      'OKX订单ID', '状态', '备注'
    ];
    
    let csv = headers.join(',') + '\n';
    
    for (const trade of trades) {
      const row = [
        trade.id,
        trade.trade_time,
        trade.symbol,
        trade.trade_type,
        trade.side,
        trade.order_type,
        trade.price,
        trade.size,
        trade.usdt_amount,
        trade.leverage,
        trade.fee || '',
        trade.pnl || '',
        trade.pnl_rate || '',
        trade.okx_order_id || '',
        trade.status,
        (trade.notes || '').replace(/,/g, '；') // 替换逗号避免CSV格式问题
      ];
      csv += row.join(',') + '\n';
    }
    
    return new Response(csv, {
      headers: {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': `attachment; filename="trade_history_${accountId}_${Date.now()}.csv"`
      }
    });
  } catch (error: any) {
    console.error('导出交易历史失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 记录交易历史（内部使用）
 * POST /trade-history/record
 */
liveTradingRoutesV2.post('/trade-history/record', async (c) => {
  try {
    const body = await c.req.json();
    const {
      accountId, positionId, tradeType, symbol, side, orderType,
      price, size, usdtAmount, leverage, fee, pnl, pnlRate,
      okxOrderId, status, notes
    } = body;
    
    await c.env.DB.prepare(`
      INSERT INTO trade_history (
        account_id, position_id, trade_type, symbol, side, order_type,
        price, size, usdt_amount, leverage, fee, pnl, pnl_rate,
        okx_order_id, status, notes
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).bind(
      accountId, positionId, tradeType, symbol, side, orderType,
      price, size, usdtAmount, leverage, fee, pnl, pnlRate,
      okxOrderId, status, notes
    ).run();
    
    return c.json({ success: true });
  } catch (error: any) {
    console.error('记录交易历史失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 取消指定的委托单
 * POST /orders/cancel-specific
 */
liveTradingRoutesV2.post('/orders/cancel-specific', async (c) => {
  try {
    const body = await c.req.json();
    const { accountId, orderId, symbol } = body;
    
    if (!accountId || !orderId || !symbol) {
      return c.json({ success: false, error: '缺少必要参数' }, 400);
    }

    const api = await getOKXAPIByAccount(c.env.DB, accountId);
    
    console.log(`尝试取消订单: symbol=${symbol}, orderId=${orderId}`);
    
    const result = await api.cancelOrder(symbol, orderId);
    
    console.log('OKX取消订单返回:', JSON.stringify(result));
    
    if (result.code === '0') {
      // 更新数据库订单状态
      await c.env.DB.prepare(`
        UPDATE live_orders 
        SET status = 'cancelled', updated_at = datetime('now')
        WHERE okx_order_id = ? AND account_id = ?
      `).bind(orderId, accountId).run();
      
      return c.json({
        success: true,
        message: '订单已取消',
        data: result.data
      });
    } else {
      return c.json({
        success: false,
        error: result.msg || '取消失败',
        code: result.code
      }, 400);
    }
  } catch (error: any) {
    console.error('取消指定委托单失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 获取未成交的委托单列表
 * GET /orders/pending-list
 */
liveTradingRoutesV2.get('/orders/pending-list', async (c) => {
  try {
    const accountId = c.req.query('accountId') || '';
    if (!accountId) {
      return c.json({ success: false, error: '缺少accountId参数' }, 400);
    }

    const api = await getOKXAPIByAccount(c.env.DB, accountId);
    
    // 获取所有未成交的委托单
    const pendingOrders = await api.getPendingOrders();
    
    // 格式化订单信息
    const formattedOrders = pendingOrders.map((order: any) => ({
      orderId: order.ordId,
      symbol: order.instId,
      side: order.side,
      orderType: order.ordType,
      price: order.px,
      size: order.sz,
      filledSize: order.accFillSz,
      state: order.state,
      createTime: order.cTime,
      updateTime: order.uTime
    }));
    
    return c.json({
      success: true,
      orders: formattedOrders,
      total: formattedOrders.length
    });
  } catch (error: any) {
    console.error('获取未成交委托单列表失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 取消所有未成交的委托单
 * DELETE /orders/cancel-all-pending
 */
liveTradingRoutesV2.delete('/orders/cancel-all-pending', async (c) => {
  try {
    const accountId = c.req.query('accountId') || '';
    if (!accountId) {
      return c.json({ success: false, error: '缺少accountId参数' }, 400);
    }

    const api = await getOKXAPIByAccount(c.env.DB, accountId);
    
    // 获取所有未成交的委托单（挂单状态）
    const pendingOrders = await api.getPendingOrders();
    
    if (!pendingOrders || pendingOrders.length === 0) {
      return c.json({
        success: true,
        canceledCount: 0,
        message: '没有未成交的委托单'
      });
    }
    
    let canceledCount = 0;
    const errors: string[] = [];
    
    // 批量取消委托单
    for (const order of pendingOrders) {
      try {
        // 从instId提取symbol (例如: "FIL-USDT-SWAP" -> "FIL")
        const symbol = order.instId.split('-')[0];
        const result = await api.cancelOrder(symbol, order.ordId);
        
        if (result.code === '0') {
          canceledCount++;
          
          // 更新数据库订单状态
          await c.env.DB.prepare(`
            UPDATE live_orders 
            SET status = 'cancelled', updated_at = datetime('now')
            WHERE okx_order_id = ? AND account_id = ?
          `).bind(order.ordId, accountId).run();
        } else {
          errors.push(`订单 ${order.ordId}: ${result.msg}`);
        }
      } catch (error: any) {
        errors.push(`订单 ${order.ordId}: ${error.message}`);
      }
    }
    
    return c.json({
      success: canceledCount > 0,
      canceledCount,
      totalOrders: pendingOrders.length,
      errors: errors.length > 0 ? errors : undefined,
      message: `成功取消 ${canceledCount}/${pendingOrders.length} 个委托单`
    });
  } catch (error: any) {
    console.error('取消所有未成交委托单失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

// 📦 批量交易路由已移至 src/routes/batchTradingRoutes.ts
// 请使用 /api/live-trading-v2/batch/* 路由访问批量功能:
//   - POST /api/live-trading-v2/batch/order
//   - POST /api/live-trading-v2/batch/close
//   - POST /api/live-trading-v2/batch/balance
//   - POST /api/live-trading-v2/batch/positions

export default liveTradingRoutesV2;

/**
 * 获取账户配置（调试用）
 */
liveTradingRoutesV2.get('/debug/account-config', async (c) => {
  try {
    const accountId = c.req.query('accountId') || '';
    if (!accountId) {
      return c.json({ success: false, error: '缺少accountId参数' }, 400);
    }

    const api = await getOKXAPIByAccount(c.env.DB, accountId);
    
    // 获取账户配置
    const config = await api.request('GET', '/account/config');
    
    // 获取持仓模式
    const posMode = await api.request('GET', '/account/position-mode');
    
    return c.json({
      success: true,
      accountConfig: config,
      positionMode: posMode
    });
  } catch (error: any) {
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 强制平仓（尝试多种方法）
 */
liveTradingRoutesV2.post('/debug/force-close/:id', async (c) => {
  try {
    const positionId = c.req.param('id');
    const accountId = c.req.query('accountId') || '';
    
    if (!accountId) {
      return c.json({ success: false, error: '缺少accountId参数' }, 400);
    }

    const api = await getOKXAPIByAccount(c.env.DB, accountId);
    const positions = await api.getAllPositions();
    const position = positions.find((pos: any) => pos.posId === positionId);

    if (!position) {
      return c.json({ success: false, error: '未找到持仓' }, 404);
    }

    const instId = position.instId;
    const posSide = position.posSide;
    const size = Math.abs(parseFloat(position.pos));
    
    const results = [];
    
    // 方法1: 不带posSide参数（单向持仓模式）
    try {
      const result1 = await api.request('POST', '/trade/order', {
        instId,
        tdMode: 'cross',
        side: posSide === 'long' ? 'sell' : 'buy',
        ordType: 'market',
        sz: size.toString(),
        reduceOnly: true,
      });
      results.push({ method: 'without_posSide', result: result1 });
    } catch (e: any) {
      results.push({ method: 'without_posSide', error: e.message });
    }
    
    // 方法2: 使用net模式
    try {
      const result2 = await api.request('POST', '/trade/order', {
        instId,
        tdMode: 'cross',
        side: posSide === 'long' ? 'sell' : 'buy',
        ordType: 'market',
        sz: size.toString(),
        posSide: 'net',
        reduceOnly: true,
      });
      results.push({ method: 'net_mode', result: result2 });
    } catch (e: any) {
      results.push({ method: 'net_mode', error: e.message });
    }
    
    // 方法3: 使用原有的long_short_mode
    try {
      const result3 = await api.request('POST', '/trade/order', {
        instId,
        tdMode: 'cross',
        side: posSide === 'long' ? 'sell' : 'buy',
        ordType: 'market',
        sz: size.toString(),
        posSide: posSide,
        reduceOnly: true,
      });
      results.push({ method: 'long_short_mode', result: result3 });
    } catch (e: any) {
      results.push({ method: 'long_short_mode', error: e.message });
    }

    return c.json({
      success: true,
      position: { instId, posSide, size },
      attempts: results
    });
  } catch (error: any) {
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});


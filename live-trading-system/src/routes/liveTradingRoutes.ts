/**
 * OKX实盘交易路由
 */
import { Hono } from 'hono';
import type { Bindings } from '../types';
import OKXTradingAPI from '../../okex-trading-api.js';
import PositionMonitor, { createPositionMonitor } from '../../position-monitor.js';

const liveTradingRoutes = new Hono<{ Bindings: Bindings }>();

// 全局变量存储API实例和监控器
let okxAPI: OKXTradingAPI | null = null;
let positionMonitor: PositionMonitor | null = null;

/**
 * 获取OKX API实例
 */
async function getOKXAPI(db: any): Promise<OKXTradingAPI> {
  if (okxAPI) {
    return okxAPI;
  }

  // 从数据库读取配置
  const config = await db.prepare(`
    SELECT * FROM live_trading_config 
    WHERE is_active = 1 
    ORDER BY id DESC 
    LIMIT 1
  `).first();

  if (!config) {
    throw new Error('未找到有效的API配置，请先配置API密钥');
  }

  okxAPI = new OKXTradingAPI(
    config.api_key,
    config.api_secret,
    config.passphrase,
    config.is_testnet === 1
  );

  return okxAPI;
}

/**
 * 获取持仓监控器实例
 */
function getPositionMonitor(db: any): PositionMonitor {
  if (!positionMonitor) {
    positionMonitor = createPositionMonitor(db);
    positionMonitor.start();
  }
  return positionMonitor;
}

/**
 * 获取账户信息
 */
liveTradingRoutes.get('/account', async (c) => {
  try {
    const api = await getOKXAPI(c.env.DB);
    const balance = await api.getBalance();
    
    const usdtData = balance.data?.[0]?.details?.find((d: any) => d.ccy === 'USDT');
    
    return c.json({
      success: true,
      account: {
        totalEquity: parseFloat(usdtData?.eq || '0'),
        availableBalance: parseFloat(usdtData?.availBal || '0'),
        unrealizedPnl: parseFloat(usdtData?.upl || '0'),
        realizedPnl: 0, // OKX API暂不直接提供，需从历史记录计算
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
 * 限价委托下单
 */
liveTradingRoutes.post('/order/limit', async (c) => {
  try {
    const body = await c.req.json();
    const { symbol, side, priceType, leverage, usdtAmount } = body;

    if (!symbol || !side || !priceType || !leverage || !usdtAmount) {
      return c.json({
        success: false,
        error: '缺少必要参数'
      }, 400);
    }

    const api = await getOKXAPI(c.env.DB);
    const result = await api.limitOrder({
      symbol,
      side,
      priceType,
      leverage,
      usdtAmount
    });

    // 保存订单记录到数据库
    if (result.code === '0') {
      const orderId = result.data[0].ordId;
      await c.env.DB.prepare(`
        INSERT INTO live_orders (
          symbol, side, order_type, price_type, usdt_amount, leverage, 
          okx_order_id, status, created_at
        ) VALUES (?, ?, 'limit', ?, ?, ?, ?, 'pending', datetime('now'))
      `).run(symbol, side, priceType, usdtAmount, leverage, orderId);
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
liveTradingRoutes.post('/order/market', async (c) => {
  try {
    const body = await c.req.json();
    const { symbol, side, leverage, usdtAmount } = body;

    if (!symbol || !side || !leverage || !usdtAmount) {
      return c.json({
        success: false,
        error: '缺少必要参数'
      }, 400);
    }

    const api = await getOKXAPI(c.env.DB);
    const result = await api.marketOrder({
      symbol,
      side,
      leverage,
      usdtAmount
    });

    // 保存订单记录到数据库
    if (result.code === '0') {
      const orderId = result.data[0].ordId;
      await c.env.DB.prepare(`
        INSERT INTO live_orders (
          symbol, side, order_type, usdt_amount, leverage, 
          okx_order_id, status, created_at
        ) VALUES (?, ?, 'market', ?, ?, ?, 'pending', datetime('now'))
      `).run(symbol, side, usdtAmount, leverage, orderId);
    }

    return c.json({
      success: result.code === '0',
      data: result.data,
      error: result.msg
    });
  } catch (error: any) {
    console.error('市价委托失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 获取所有持仓
 */
liveTradingRoutes.get('/positions', async (c) => {
  try {
    const api = await getOKXAPI(c.env.DB);
    const positions = await api.getAllPositions();

    // 过滤出有持仓的数据并格式化
    const activePositions = positions
      .filter((pos: any) => parseFloat(pos.pos) !== 0)
      .map((pos: any) => {
        const entryPrice = parseFloat(pos.avgPx);
        const currentPrice = parseFloat(pos.last);
        const pnl = parseFloat(pos.upl);
        const pnlRate = ((currentPrice - entryPrice) / entryPrice) * 100 * (pos.posSide === 'long' ? 1 : -1);

        return {
          id: pos.posId,
          symbol: pos.instId.split('-')[0],
          side: pos.posSide,
          entryPrice,
          currentPrice,
          size: Math.abs(parseFloat(pos.pos)),
          leverage: parseInt(pos.lever),
          usdtAmount: parseFloat(pos.margin),
          pnl,
          pnlRate,
          tpPrice: pos.tpTriggerPx ? parseFloat(pos.tpTriggerPx) : null,
          slPrice: pos.slTriggerPx ? parseFloat(pos.slTriggerPx) : null,
          tpRate: null,
          slRate: null,
          maxHoldingCandles: 0,
          currentHoldingCandles: 0,
          candleInterval: '5m'
        };
      });

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
 * 设置止盈止损 - 固定数量
 */
liveTradingRoutes.post('/position/:id/tpsl/partial', async (c) => {
  try {
    const positionId = c.req.param('id');
    const body = await c.req.json();
    const { symbol, side, takeProfit, stopLoss } = body;

    const api = await getOKXAPI(c.env.DB);
    const result = await api.setPartialTPSL({
      symbol,
      side,
      takeProfit,
      stopLoss
    });

    return c.json({
      success: true,
      data: result
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
 * 设置止盈止损 - 全部仓位
 */
liveTradingRoutes.post('/position/:id/tpsl/full', async (c) => {
  try {
    const positionId = c.req.param('id');
    const body = await c.req.json();
    const { symbol, side, takeProfit, stopLoss } = body;

    const api = await getOKXAPI(c.env.DB);
    const result = await api.setFullTPSL({
      symbol,
      side,
      takeProfit,
      stopLoss
    });

    return c.json({
      success: true,
      data: result
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
 * 平仓
 */
liveTradingRoutes.post('/position/:id/close', async (c) => {
  try {
    const positionId = c.req.param('id');
    
    // 从OKX获取持仓信息
    const api = await getOKXAPI(c.env.DB);
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
    
    const result = await api.closePosition(symbol, side);

    return c.json({
      success: result.code === '0',
      data: result.data,
      error: result.msg
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
 * 获取历史记录
 */
liveTradingRoutes.get('/history', async (c) => {
  try {
    const history = await c.env.DB.prepare(`
      SELECT * FROM live_positions 
      WHERE status = 'closed' 
      ORDER BY exit_time DESC 
      LIMIT 50
    `).all();

    return c.json({
      success: true,
      history: history.results || []
    });
  } catch (error: any) {
    console.error('获取历史记录失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 获取API配置
 */
liveTradingRoutes.get('/config', async (c) => {
  try {
    const config = await c.env.DB.prepare(`
      SELECT api_key, is_testnet FROM live_trading_config 
      WHERE is_active = 1 
      ORDER BY id DESC 
      LIMIT 1
    `).first();

    return c.json({
      success: true,
      config: config ? {
        apiKey: config.api_key,
        apiSecret: '********', // 不返回完整密钥
        passphrase: '********',
        isTestnet: config.is_testnet === 1
      } : null
    });
  } catch (error: any) {
    console.error('获取配置失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 保存API配置
 */
liveTradingRoutes.post('/config', async (c) => {
  try {
    const body = await c.req.json();
    const { apiKey, apiSecret, passphrase, isTestnet } = body;

    if (!apiKey || !apiSecret || !passphrase) {
      return c.json({
        success: false,
        error: '缺少必要的配置参数'
      }, 400);
    }

    // 停用旧配置
    await c.env.DB.prepare(`
      UPDATE live_trading_config SET is_active = 0
    `).run();

    // 插入新配置
    await c.env.DB.prepare(`
      INSERT INTO live_trading_config (
        api_key, api_secret, passphrase, is_testnet, is_active
      ) VALUES (?, ?, ?, ?, 1)
    `).run(apiKey, apiSecret, passphrase, isTestnet ? 1 : 0);

    // 清除旧的API实例，下次调用时会重新创建
    okxAPI = null;

    return c.json({
      success: true,
      message: '配置保存成功'
    });
  } catch (error: any) {
    console.error('保存配置失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 设置持仓最长持仓周期
 */
liveTradingRoutes.post('/position/:id/max-holding', async (c) => {
  try {
    const positionId = c.req.param('id');
    const body = await c.req.json();
    const { maxCandles, interval } = body;

    const monitor = getPositionMonitor(c.env.DB);
    await monitor.setMaxHoldingPeriod(parseInt(positionId), maxCandles, interval || '5m');

    return c.json({
      success: true,
      message: '设置成功'
    });
  } catch (error: any) {
    console.error('设置持仓周期失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

/**
 * 获取即将到期的持仓
 */
liveTradingRoutes.get('/positions/expiring', async (c) => {
  try {
    const monitor = getPositionMonitor(c.env.DB);
    const positions = await monitor.getExpiringPositions(5);

    return c.json({
      success: true,
      positions
    });
  } catch (error: any) {
    console.error('获取即将到期持仓失败:', error);
    return c.json({
      success: false,
      error: error.message
    }, 500);
  }
});

export default liveTradingRoutes;

import OKXTradingAPI from '../../okex-trading-api.js'

// API实例缓存（按账户ID）
const apiCache = new Map<string, OKXTradingAPI>()

/**
 * 根据账户ID获取OKX API实例
 */
export async function getOKXAPIByAccount(db: any, accountId: string): Promise<OKXTradingAPI> {
  // 检查缓存
  if (apiCache.has(accountId)) {
    return apiCache.get(accountId)!
  }

  // 从数据库读取配置
  const config = await db.prepare(`
    SELECT * FROM live_trading_accounts 
    WHERE id = ?
  `).bind(accountId).first()

  if (!config) {
    throw new Error('未找到有效的API配置')
  }

  const api = new OKXTradingAPI(
    config.api_key,
    config.secret_key,
    config.passphrase,
    config.is_testnet === 1
  )

  // 缓存实例
  apiCache.set(accountId, api)

  return api
}

/**
 * 清除API缓存
 */
export function clearAPICache(accountId?: string) {
  if (accountId) {
    apiCache.delete(accountId)
  } else {
    apiCache.clear()
  }
}

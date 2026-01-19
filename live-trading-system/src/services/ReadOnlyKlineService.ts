/**
 * 只读K线数据服务
 * 
 * 🔒 安全规则：
 * - K线数据库（kline_data表）只允许 KlineService 写入
 * - 其他业务逻辑只能通过 ReadOnlyKlineService 读取
 * - 任何尝试通过 ReadOnlyKlineService 写入的操作都会抛出错误
 * 
 * 📝 使用示例：
 * ```typescript
 * const klineService = new ReadOnlyKlineService(c.env.DB);
 * const data = await klineService.getKlineWithIndicators('BTC', '5m', 100);
 * ```
 */

import { KlineService } from './klineService';

export class ReadOnlyKlineService extends KlineService {
  /**
   * 覆盖所有写入方法，抛出错误
   */
  
  async syncKlineData(): Promise<any> {
    throw new Error('🔒 安全错误：K线数据库只读！请使用 KlineService 进行数据同步。当前服务：ReadOnlyKlineService');
  }
  
  async saveKlineData(): Promise<any> {
    throw new Error('🔒 安全错误：K线数据库只读！请使用 KlineService 进行数据保存。当前服务：ReadOnlyKlineService');
  }
  
  async updateKlineData(): Promise<any> {
    throw new Error('🔒 安全错误：K线数据库只读！请使用 KlineService 进行数据更新。当前服务：ReadOnlyKlineService');
  }
  
  async deleteKlineData(): Promise<any> {
    throw new Error('🔒 安全错误：K线数据库只读！请使用 KlineService 进行数据删除。当前服务：ReadOnlyKlineService');
  }
  
  async insertKline(): Promise<any> {
    throw new Error('🔒 安全错误：K线数据库只读！请使用 KlineService 进行数据插入。当前服务：ReadOnlyKlineService');
  }
  
  async batchInsertKlines(): Promise<any> {
    throw new Error('🔒 安全错误：K线数据库只读！请使用 KlineService 进行批量插入。当前服务：ReadOnlyKlineService');
  }
  
  /**
   * ✅ 允许的只读方法
   * - getKlineWithIndicators
   * - getKlineData
   * - getLatestKline
   * - countKlines
   * 等所有读取方法
   */
}

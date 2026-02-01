/**
 * K线数据库访问守卫
 * 
 * 🔒 安全规则：
 * 1. 只有 KlineService 可以写入 kline_data 表
 * 2. 其他所有服务只能读取 kline_data 表
 * 3. 违反规则会抛出错误
 */

export class KlineDbGuard {
  private static readonly KLINE_TABLE = 'kline_data';
  private static readonly WRITE_ALLOWED_SERVICES = [
    'KlineService',
    'kline-sync', // K线同步操作
  ];

  /**
   * 检查是否允许写入K线数据表
   * @param callerName 调用者名称（服务名或操作名）
   * @throws Error 如果不允许写入
   */
  static checkWritePermission(callerName: string): void {
    if (!this.WRITE_ALLOWED_SERVICES.includes(callerName)) {
      throw new Error(
        `🔒 [数据库安全] 禁止写入kline_data表！` +
        `调用者: ${callerName}。` +
        `只有 ${this.WRITE_ALLOWED_SERVICES.join(', ')} 可以写入K线数据。`
      );
    }
  }

  /**
   * 检查SQL语句是否试图修改K线数据表
   * @param sql SQL语句
   * @param callerName 调用者名称
   * @throws Error 如果SQL试图修改kline_data且调用者无权限
   */
  static validateQuery(sql: string, callerName: string): void {
    const normalizedSql = sql.toLowerCase().trim();
    
    // 检查是否是写操作
    const isWriteOperation = 
      normalizedSql.startsWith('insert') ||
      normalizedSql.startsWith('update') ||
      normalizedSql.startsWith('delete') ||
      normalizedSql.startsWith('replace');

    // 检查是否操作kline_data表
    const isKlineTable = normalizedSql.includes(this.KLINE_TABLE);

    // 如果是写操作且操作kline_data表，检查权限
    if (isWriteOperation && isKlineTable) {
      this.checkWritePermission(callerName);
    }
  }

  /**
   * 包装数据库查询，自动进行权限检查
   */
  static wrapQuery(db: D1Database, callerName: string) {
    return {
      prepare: (sql: string) => {
        this.validateQuery(sql, callerName);
        return db.prepare(sql);
      },
      batch: (statements: any[]) => {
        // 检查batch中的所有语句
        statements.forEach(stmt => {
          if (stmt && stmt.statement) {
            this.validateQuery(stmt.statement, callerName);
          }
        });
        return db.batch(statements);
      },
      exec: (sql: string) => {
        this.validateQuery(sql, callerName);
        return db.exec(sql);
      }
    };
  }
}

/**
 * 使用示例：
 * 
 * // 在KlineService中（允许写入）
 * KlineDbGuard.checkWritePermission('KlineService'); // ✅ 通过
 * 
 * // 在其他服务中（只读）
 * KlineDbGuard.checkWritePermission('BacktestService'); // ❌ 抛出错误
 * 
 * // 自动检查SQL
 * const guardedDb = KlineDbGuard.wrapQuery(db, 'BacktestService');
 * guardedDb.prepare('SELECT * FROM kline_data'); // ✅ 读取允许
 * guardedDb.prepare('DELETE FROM kline_data'); // ❌ 抛出错误
 */

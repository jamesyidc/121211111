/**
 * Live Trading Storage Adapter
 * Provides unified interface for both Database and JSONL storage
 */

import type { D1Database } from '@cloudflare/workers-types';
import * as jsonlStorage from './jsonlStorageService';

// Configuration: Set to 'jsonl' to use JSONL files, 'database' to use SQLite
const STORAGE_MODE: 'database' | 'jsonl' = process.env.STORAGE_MODE === 'jsonl' ? 'jsonl' : 'database';

console.log(`🗄️  Live Trading Storage Mode: ${STORAGE_MODE.toUpperCase()}`);

/**
 * Account Operations
 */
export async function getAllAccounts(db?: D1Database): Promise<any[]> {
  if (STORAGE_MODE === 'jsonl') {
    return await jsonlStorage.getAllAccounts();
  }
  
  if (!db) throw new Error('Database required for database mode');
  const result = await db.prepare(`
    SELECT * FROM live_trading_accounts ORDER BY created_at DESC
  `).all();
  return result.results || [];
}

export async function getAccountById(id: string, db?: D1Database): Promise<any | null> {
  if (STORAGE_MODE === 'jsonl') {
    return await jsonlStorage.getAccountById(id);
  }
  
  if (!db) throw new Error('Database required for database mode');
  const result = await db.prepare(`
    SELECT * FROM live_trading_accounts WHERE id = ?
  `).bind(id).first();
  return result || null;
}

export async function addAccount(account: any, db?: D1Database): Promise<void> {
  if (STORAGE_MODE === 'jsonl') {
    return await jsonlStorage.addAccount(account);
  }
  
  if (!db) throw new Error('Database required for database mode');
  await db.prepare(`
    INSERT INTO live_trading_accounts 
    (id, name, api_key, secret_key, passphrase, is_testnet, initial_balance, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `).bind(
    account.id,
    account.name,
    account.api_key,
    account.secret_key,
    account.passphrase,
    account.is_testnet,
    account.initial_balance,
    account.created_at
  ).run();
}

export async function updateAccount(id: string, updates: any, db?: D1Database): Promise<void> {
  if (STORAGE_MODE === 'jsonl') {
    return await jsonlStorage.updateAccount(id, updates);
  }
  
  if (!db) throw new Error('Database required for database mode');
  const fields = Object.keys(updates).map(k => `${k} = ?`).join(', ');
  const values = Object.values(updates);
  await db.prepare(`
    UPDATE live_trading_accounts SET ${fields} WHERE id = ?
  `).bind(...values, id).run();
}

export async function deleteAccount(id: string, db?: D1Database): Promise<void> {
  if (STORAGE_MODE === 'jsonl') {
    return await jsonlStorage.deleteAccount(id);
  }
  
  if (!db) throw new Error('Database required for database mode');
  // Delete related data first
  await db.prepare(`DELETE FROM defense_add_config WHERE account_id = ?`).bind(id).run();
  await db.prepare(`DELETE FROM position_tpsl_config WHERE account_id = ?`).bind(id).run();
  await db.prepare(`DELETE FROM live_orders WHERE account_id = ?`).bind(id).run();
  await db.prepare(`DELETE FROM trade_history WHERE account_id = ?`).bind(id).run();
  await db.prepare(`DELETE FROM live_positions WHERE account_id = ?`).bind(id).run();
  await db.prepare(`DELETE FROM live_trading_accounts WHERE id = ?`).bind(id).run();
}

/**
 * Position Operations
 */
export async function getPositionsByAccount(accountId: string, db?: D1Database): Promise<any[]> {
  if (STORAGE_MODE === 'jsonl') {
    return await jsonlStorage.getPositionsByAccount(accountId);
  }
  
  if (!db) throw new Error('Database required for database mode');
  const result = await db.prepare(`
    SELECT * FROM live_positions WHERE account_id = ? AND status = 'open'
    ORDER BY created_at DESC
  `).bind(accountId).all();
  return result.results || [];
}

export async function getPositionById(id: string, db?: D1Database): Promise<any | null> {
  if (STORAGE_MODE === 'jsonl') {
    return await jsonlStorage.getPositionById(id);
  }
  
  if (!db) throw new Error('Database required for database mode');
  const result = await db.prepare(`
    SELECT * FROM live_positions WHERE id = ?
  `).bind(id).first();
  return result || null;
}

export async function addPosition(position: any, db?: D1Database): Promise<void> {
  if (STORAGE_MODE === 'jsonl') {
    return await jsonlStorage.addPosition(position);
  }
  
  if (!db) throw new Error('Database required for database mode');
  const fields = Object.keys(position).join(', ');
  const placeholders = Object.keys(position).map(() => '?').join(', ');
  const values = Object.values(position);
  
  await db.prepare(`
    INSERT INTO live_positions (${fields}) VALUES (${placeholders})
  `).bind(...values).run();
}

export async function updatePosition(id: string, updates: any, db?: D1Database): Promise<void> {
  if (STORAGE_MODE === 'jsonl') {
    return await jsonlStorage.updatePosition(id, updates);
  }
  
  if (!db) throw new Error('Database required for database mode');
  const fields = Object.keys(updates).map(k => `${k} = ?`).join(', ');
  const values = Object.values(updates);
  await db.prepare(`
    UPDATE live_positions SET ${fields}, updated_at = CURRENT_TIMESTAMP WHERE id = ?
  `).bind(...values, id).run();
}

/**
 * Trade History Operations
 */
export async function getTradeHistoryByAccount(accountId: string, filters: any = {}, db?: D1Database): Promise<any[]> {
  if (STORAGE_MODE === 'jsonl') {
    let history = await jsonlStorage.getTradeHistoryByAccount(accountId);
    
    // Apply filters
    if (filters.symbol) {
      history = history.filter(t => t.symbol === filters.symbol);
    }
    if (filters.trade_type) {
      history = history.filter(t => t.trade_type === filters.trade_type);
    }
    if (filters.days) {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - filters.days);
      history = history.filter(t => new Date(t.trade_time) >= cutoffDate);
    }
    
    return history.sort((a, b) => 
      new Date(b.trade_time).getTime() - new Date(a.trade_time).getTime()
    );
  }
  
  if (!db) throw new Error('Database required for database mode');
  let query = `SELECT * FROM trade_history WHERE account_id = ?`;
  const params: any[] = [accountId];
  
  if (filters.symbol) {
    query += ` AND symbol = ?`;
    params.push(filters.symbol);
  }
  if (filters.trade_type) {
    query += ` AND trade_type = ?`;
    params.push(filters.trade_type);
  }
  if (filters.days) {
    query += ` AND trade_time >= datetime('now', '-${filters.days} days')`;
  }
  
  query += ` ORDER BY trade_time DESC LIMIT 1000`;
  
  const result = await db.prepare(query).bind(...params).all();
  return result.results || [];
}

export async function addTradeHistory(trade: any, db?: D1Database): Promise<void> {
  if (STORAGE_MODE === 'jsonl') {
    return await jsonlStorage.addTradeHistory(trade);
  }
  
  if (!db) throw new Error('Database required for database mode');
  const fields = Object.keys(trade).join(', ');
  const placeholders = Object.keys(trade).map(() => '?').join(', ');
  const values = Object.values(trade);
  
  await db.prepare(`
    INSERT INTO trade_history (${fields}) VALUES (${placeholders})
  `).bind(...values).run();
}

/**
 * TPSL Config Operations
 */
export async function getTPSLConfigByPosition(positionId: string, db?: D1Database): Promise<any | null> {
  if (STORAGE_MODE === 'jsonl') {
    return await jsonlStorage.getTPSLConfigByPosition(positionId);
  }
  
  if (!db) throw new Error('Database required for database mode');
  const result = await db.prepare(`
    SELECT * FROM position_tpsl_config WHERE position_id = ?
  `).bind(positionId).first();
  return result || null;
}

export async function addTPSLConfig(config: any, db?: D1Database): Promise<void> {
  if (STORAGE_MODE === 'jsonl') {
    return await jsonlStorage.addTPSLConfig(config);
  }
  
  if (!db) throw new Error('Database required for database mode');
  const fields = Object.keys(config).join(', ');
  const placeholders = Object.keys(config).map(() => '?').join(', ');
  const values = Object.values(config);
  
  await db.prepare(`
    INSERT INTO position_tpsl_config (${fields}) VALUES (${placeholders})
  `).bind(...values).run();
}

export async function updateTPSLConfig(id: string, updates: any, db?: D1Database): Promise<void> {
  if (STORAGE_MODE === 'jsonl') {
    return await jsonlStorage.updateTPSLConfig(id, updates);
  }
  
  if (!db) throw new Error('Database required for database mode');
  const fields = Object.keys(updates).map(k => `${k} = ?`).join(', ');
  const values = Object.values(updates);
  await db.prepare(`
    UPDATE position_tpsl_config SET ${fields}, updated_at = CURRENT_TIMESTAMP WHERE id = ?
  `).bind(...values, id).run();
}

/**
 * Defense Config Operations
 */
export async function getDefenseConfigsByPosition(positionId: string, db?: D1Database): Promise<any[]> {
  if (STORAGE_MODE === 'jsonl') {
    return await jsonlStorage.getDefenseConfigsByPosition(positionId);
  }
  
  if (!db) throw new Error('Database required for database mode');
  const result = await db.prepare(`
    SELECT * FROM defense_add_config WHERE position_id = ? ORDER BY created_at DESC
  `).bind(positionId).all();
  return result.results || [];
}

export async function addDefenseConfig(config: any, db?: D1Database): Promise<void> {
  if (STORAGE_MODE === 'jsonl') {
    return await jsonlStorage.addDefenseConfig(config);
  }
  
  if (!db) throw new Error('Database required for database mode');
  const fields = Object.keys(config).join(', ');
  const placeholders = Object.keys(config).map(() => '?').join(', ');
  const values = Object.values(config);
  
  await db.prepare(`
    INSERT INTO defense_add_config (${fields}) VALUES (${placeholders})
  `).bind(...values).run();
}

export async function deleteDefenseConfig(id: string, db?: D1Database): Promise<void> {
  if (STORAGE_MODE === 'jsonl') {
    return await jsonlStorage.deleteDefenseConfig(id);
  }
  
  if (!db) throw new Error('Database required for database mode');
  await db.prepare(`DELETE FROM defense_add_config WHERE id = ?`).bind(id).run();
}

export async function deleteDefenseConfigsByPosition(positionId: string, db?: D1Database): Promise<void> {
  if (STORAGE_MODE === 'jsonl') {
    return await jsonlStorage.deleteDefenseConfigsByPosition(positionId);
  }
  
  if (!db) throw new Error('Database required for database mode');
  await db.prepare(`DELETE FROM defense_add_config WHERE position_id = ?`).bind(positionId).run();
}

/**
 * Utility functions
 */
export function generateId(prefix: string = ''): string {
  return jsonlStorage.generateId(prefix);
}

export function getCurrentTimestamp(): string {
  return jsonlStorage.getCurrentTimestamp();
}

// Export storage mode for conditional logic
export { STORAGE_MODE };

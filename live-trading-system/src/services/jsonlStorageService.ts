/**
 * JSONL Storage Service
 * Handles reading/writing trading data to JSONL files instead of database
 */

import * as fs from 'fs';
import * as path from 'path';
import * as readline from 'readline';

// Data directory for JSONL files
const DATA_DIR = path.join(process.cwd(), 'data', 'trading');

// Ensure data directory exists
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

// File paths
const FILES = {
  ACCOUNTS: path.join(DATA_DIR, 'accounts.jsonl'),
  POSITIONS: path.join(DATA_DIR, 'positions.jsonl'),
  ORDERS: path.join(DATA_DIR, 'orders.jsonl'),
  TRADE_HISTORY: path.join(DATA_DIR, 'trade_history.jsonl'),
  TPSL_CONFIG: path.join(DATA_DIR, 'tpsl_config.jsonl'),
  DEFENSE_CONFIG: path.join(DATA_DIR, 'defense_config.jsonl'),
};

/**
 * Read all records from a JSONL file
 */
export async function readJSONL<T>(filePath: string): Promise<T[]> {
  if (!fs.existsSync(filePath)) {
    return [];
  }

  const records: T[] = [];
  const fileStream = fs.createReadStream(filePath);
  const rl = readline.createInterface({
    input: fileStream,
    crlfDelay: Infinity,
  });

  for await (const line of rl) {
    if (line.trim()) {
      try {
        records.push(JSON.parse(line));
      } catch (error) {
        console.error(`Error parsing line in ${filePath}:`, line, error);
      }
    }
  }

  return records;
}

/**
 * Append a record to a JSONL file
 */
export async function appendJSONL<T>(filePath: string, record: T): Promise<void> {
  const line = JSON.stringify(record) + '\n';
  await fs.promises.appendFile(filePath, line, 'utf8');
}

/**
 * Write all records to a JSONL file (overwrite)
 */
export async function writeJSONL<T>(filePath: string, records: T[]): Promise<void> {
  const content = records.map(r => JSON.stringify(r)).join('\n') + '\n';
  await fs.promises.writeFile(filePath, content, 'utf8');
}

/**
 * Update records in JSONL file by filter function
 */
export async function updateJSONL<T extends { id?: any }>(
  filePath: string,
  filter: (record: T) => boolean,
  updater: (record: T) => T
): Promise<void> {
  const records = await readJSONL<T>(filePath);
  const updated = records.map(record => filter(record) ? updater(record) : record);
  await writeJSONL(filePath, updated);
}

/**
 * Delete records from JSONL file by filter function
 */
export async function deleteJSONL<T>(
  filePath: string,
  filter: (record: T) => boolean
): Promise<void> {
  const records = await readJSONL<T>(filePath);
  const filtered = records.filter(record => !filter(record));
  await writeJSONL(filePath, filtered);
}

// ========== Account Operations ==========

export interface Account {
  id: string;
  name: string;
  api_key: string;
  secret_key: string;
  passphrase: string;
  is_testnet: number;
  initial_balance: number;
  trading_balance?: number;
  funding_balance?: number;
  daily_pnl?: number;
  last_update?: string;
  created_at: string;
  trade_time?: string;
}

export async function getAllAccounts(): Promise<Account[]> {
  return await readJSONL<Account>(FILES.ACCOUNTS);
}

export async function getAccountById(id: string): Promise<Account | null> {
  const accounts = await getAllAccounts();
  return accounts.find(a => a.id === id) || null;
}

export async function addAccount(account: Account): Promise<void> {
  await appendJSONL(FILES.ACCOUNTS, account);
}

export async function updateAccount(id: string, updates: Partial<Account>): Promise<void> {
  await updateJSONL<Account>(
    FILES.ACCOUNTS,
    (a) => a.id === id,
    (a) => ({ ...a, ...updates })
  );
}

export async function deleteAccount(id: string): Promise<void> {
  await deleteJSONL<Account>(FILES.ACCOUNTS, (a) => a.id === id);
  
  // Also delete related data
  await deleteJSONL(FILES.POSITIONS, (p: any) => p.account_id === id);
  await deleteJSONL(FILES.ORDERS, (o: any) => o.account_id === id);
  await deleteJSONL(FILES.TRADE_HISTORY, (t: any) => t.account_id === id);
  await deleteJSONL(FILES.TPSL_CONFIG, (t: any) => t.account_id === id);
  await deleteJSONL(FILES.DEFENSE_CONFIG, (d: any) => d.account_id === id);
}

// ========== Position Operations ==========

export interface Position {
  id: string;
  account_id: string;
  symbol: string;
  side: 'long' | 'short';
  entry_price: number;
  entry_time: string;
  size: number;
  leverage: number;
  usdt_amount: number;
  okx_order_id?: string;
  okx_position_id?: string;
  tp_price?: number;
  tp_rate?: number;
  tp_order_id?: string;
  sl_price?: number;
  sl_rate?: number;
  sl_order_id?: string;
  max_holding_candles?: number;
  candle_interval?: string;
  current_holding_candles?: number;
  exit_price?: number;
  exit_time?: string;
  pnl?: number;
  pnl_rate?: number;
  close_reason?: string;
  auto_close_triggered?: number;
  status: 'open' | 'closed' | 'liquidated';
  created_at: string;
  updated_at: string;
}

export async function getAllPositions(): Promise<Position[]> {
  return await readJSONL<Position>(FILES.POSITIONS);
}

export async function getPositionsByAccount(accountId: string): Promise<Position[]> {
  const positions = await getAllPositions();
  return positions.filter(p => p.account_id === accountId && p.status === 'open');
}

export async function getPositionById(id: string): Promise<Position | null> {
  const positions = await getAllPositions();
  return positions.find(p => p.id === id) || null;
}

export async function addPosition(position: Position): Promise<void> {
  await appendJSONL(FILES.POSITIONS, position);
}

export async function updatePosition(id: string, updates: Partial<Position>): Promise<void> {
  await updateJSONL<Position>(
    FILES.POSITIONS,
    (p) => p.id === id,
    (p) => ({ ...p, ...updates, updated_at: new Date().toISOString() })
  );
}

export async function deletePosition(id: string): Promise<void> {
  await deleteJSONL<Position>(FILES.POSITIONS, (p) => p.id === id);
}

// ========== Order Operations ==========

export interface Order {
  id: string;
  account_id: string;
  position_id?: string;
  symbol: string;
  side: 'buy' | 'sell';
  order_type: 'limit' | 'market' | 'stop' | 'take_profit' | 'stop_loss';
  price?: number;
  size: number;
  usdt_amount?: number;
  leverage?: number;
  price_type?: string;
  okx_order_id?: string;
  okx_client_order_id?: string;
  filled_size?: number;
  avg_price?: number;
  fee?: number;
  status: 'pending' | 'filled' | 'partially_filled' | 'cancelled' | 'failed';
  error_msg?: string;
  created_at: string;
  updated_at: string;
}

export async function getAllOrders(): Promise<Order[]> {
  return await readJSONL<Order>(FILES.ORDERS);
}

export async function getOrdersByAccount(accountId: string): Promise<Order[]> {
  const orders = await getAllOrders();
  return orders.filter(o => o.account_id === accountId);
}

export async function getOrderById(id: string): Promise<Order | null> {
  const orders = await getAllOrders();
  return orders.find(o => o.id === id) || null;
}

export async function addOrder(order: Order): Promise<void> {
  await appendJSONL(FILES.ORDERS, order);
}

export async function updateOrder(id: string, updates: Partial<Order>): Promise<void> {
  await updateJSONL<Order>(
    FILES.ORDERS,
    (o) => o.id === id,
    (o) => ({ ...o, ...updates, updated_at: new Date().toISOString() })
  );
}

// ========== Trade History Operations ==========

export interface TradeHistory {
  id: string;
  account_id: string;
  position_id?: string;
  trade_type: string;
  symbol: string;
  side: string;
  order_type: string;
  price: number;
  size: number;
  usdt_amount: number;
  leverage: number;
  fee?: number;
  pnl?: number;
  pnl_rate?: number;
  okx_order_id?: string;
  status: string;
  trade_time: string;
  notes?: string;
}

export async function getAllTradeHistory(): Promise<TradeHistory[]> {
  return await readJSONL<TradeHistory>(FILES.TRADE_HISTORY);
}

export async function getTradeHistoryByAccount(accountId: string): Promise<TradeHistory[]> {
  const history = await getAllTradeHistory();
  return history.filter(t => t.account_id === accountId);
}

export async function addTradeHistory(trade: TradeHistory): Promise<void> {
  await appendJSONL(FILES.TRADE_HISTORY, trade);
}

// ========== TPSL Config Operations ==========

export interface TPSLConfig {
  id: string;
  account_id: string;
  position_id: string;
  take_profit_price?: number;
  take_profit_rate?: number;
  stop_loss_price?: number;
  stop_loss_rate?: number;
  max_hold_timeframe?: string;
  max_hold_bars?: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export async function getAllTPSLConfigs(): Promise<TPSLConfig[]> {
  return await readJSONL<TPSLConfig>(FILES.TPSL_CONFIG);
}

export async function getTPSLConfigByPosition(positionId: string): Promise<TPSLConfig | null> {
  const configs = await getAllTPSLConfigs();
  return configs.find(c => c.position_id === positionId) || null;
}

export async function addTPSLConfig(config: TPSLConfig): Promise<void> {
  await appendJSONL(FILES.TPSL_CONFIG, config);
}

export async function updateTPSLConfig(id: string, updates: Partial<TPSLConfig>): Promise<void> {
  await updateJSONL<TPSLConfig>(
    FILES.TPSL_CONFIG,
    (c) => c.id === id,
    (c) => ({ ...c, ...updates, updated_at: new Date().toISOString() })
  );
}

export async function deleteTPSLConfig(id: string): Promise<void> {
  await deleteJSONL<TPSLConfig>(FILES.TPSL_CONFIG, (c) => c.id === id);
}

// ========== Defense Config Operations ==========

export interface DefenseConfig {
  id: string;
  account_id: string;
  position_id: string;
  symbol: string;
  trigger_type: 'up' | 'down';
  trigger_percent: number;
  trigger_price: number;
  usdt_amount: number;
  leverage: number;
  anchor_price: number;
  status: string;
  triggered_at?: string;
  created_at: string;
  updated_at: string;
}

export async function getAllDefenseConfigs(): Promise<DefenseConfig[]> {
  return await readJSONL<DefenseConfig>(FILES.DEFENSE_CONFIG);
}

export async function getDefenseConfigsByPosition(positionId: string): Promise<DefenseConfig[]> {
  const configs = await getAllDefenseConfigs();
  return configs.filter(c => c.position_id === positionId);
}

export async function addDefenseConfig(config: DefenseConfig): Promise<void> {
  await appendJSONL(FILES.DEFENSE_CONFIG, config);
}

export async function updateDefenseConfig(id: string, updates: Partial<DefenseConfig>): Promise<void> {
  await updateJSONL<DefenseConfig>(
    FILES.DEFENSE_CONFIG,
    (c) => c.id === id,
    (c) => ({ ...c, ...updates, updated_at: new Date().toISOString() })
  );
}

export async function deleteDefenseConfig(id: string): Promise<void> {
  await deleteJSONL<DefenseConfig>(FILES.DEFENSE_CONFIG, (c) => c.id === id);
}

export async function deleteDefenseConfigsByPosition(positionId: string): Promise<void> {
  await deleteJSONL<DefenseConfig>(FILES.DEFENSE_CONFIG, (c) => c.position_id === positionId);
}

// ========== Utility Functions ==========

/**
 * Generate unique ID
 */
export function generateId(prefix: string = ''): string {
  return `${prefix}${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Get current timestamp
 */
export function getCurrentTimestamp(): string {
  return new Date().toISOString();
}

/**
 * Backup all JSONL files
 */
export async function backupAllData(): Promise<string> {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const backupDir = path.join(DATA_DIR, '..', 'backups', timestamp);
  
  if (!fs.existsSync(backupDir)) {
    fs.mkdirSync(backupDir, { recursive: true });
  }
  
  for (const [name, filePath] of Object.entries(FILES)) {
    if (fs.existsSync(filePath)) {
      const backupPath = path.join(backupDir, path.basename(filePath));
      await fs.promises.copyFile(filePath, backupPath);
    }
  }
  
  return backupDir;
}

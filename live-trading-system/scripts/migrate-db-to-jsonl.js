#!/usr/bin/env node
/**
 * Migration script: Export SQLite database to JSONL files
 * Usage: node scripts/migrate-db-to-jsonl.js
 */

import Database from 'better-sqlite3';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DB_PATH = path.join(__dirname, '..', 'trading.db');
const OUTPUT_DIR = path.join(__dirname, '..', 'data', 'trading');

// Ensure output directory exists
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

const FILES = {
  ACCOUNTS: path.join(OUTPUT_DIR, 'accounts.jsonl'),
  POSITIONS: path.join(OUTPUT_DIR, 'positions.jsonl'),
  ORDERS: path.join(OUTPUT_DIR, 'orders.jsonl'),
  TRADE_HISTORY: path.join(OUTPUT_DIR, 'trade_history.jsonl'),
  TPSL_CONFIG: path.join(OUTPUT_DIR, 'tpsl_config.jsonl'),
  DEFENSE_CONFIG: path.join(OUTPUT_DIR, 'defense_config.jsonl'),
};

/**
 * Write records to JSONL file
 */
function writeJSONL(filePath, records) {
  const content = records.map(r => JSON.stringify(r)).join('\n') + (records.length > 0 ? '\n' : '');
  fs.writeFileSync(filePath, content, 'utf8');
  console.log(`✅ Wrote ${records.length} records to ${path.basename(filePath)}`);
}

/**
 * Check if table exists
 */
function tableExists(db, tableName) {
  const result = db.prepare(`
    SELECT name FROM sqlite_master WHERE type='table' AND name=?
  `).get(tableName);
  return !!result;
}

/**
 * Main migration function
 */
function migrateDatabase() {
  console.log('🔄 Starting database migration to JSONL...\n');

  // Check if database exists
  if (!fs.existsSync(DB_PATH)) {
    console.log(`⚠️  Database not found: ${DB_PATH}`);
    console.log('📝 Creating empty JSONL files...\n');
    
    // Create empty files
    Object.values(FILES).forEach(file => writeJSONL(file, []));
    
    console.log('\n✅ Empty JSONL files created successfully!');
    console.log(`📁 Output directory: ${OUTPUT_DIR}\n`);
    return;
  }

  const db = new Database(DB_PATH, { readonly: true });

  try {
    const stats = {};

    // 1. Migrate Accounts
    console.log('📊 Migrating accounts...');
    if (tableExists(db, 'live_trading_accounts')) {
      const accounts = db.prepare(`
        SELECT * FROM live_trading_accounts ORDER BY created_at DESC
      `).all();
      writeJSONL(FILES.ACCOUNTS, accounts);
      stats.accounts = accounts.length;
    } else {
      writeJSONL(FILES.ACCOUNTS, []);
      stats.accounts = 0;
      console.log('   ℹ️  Table not found, created empty file');
    }

    // 2. Migrate Positions
    console.log('📊 Migrating positions...');
    if (tableExists(db, 'live_positions')) {
      const positions = db.prepare(`
        SELECT * FROM live_positions WHERE status = 'open' ORDER BY created_at DESC
      `).all();
      writeJSONL(FILES.POSITIONS, positions);
      stats.positions = positions.length;
    } else {
      writeJSONL(FILES.POSITIONS, []);
      stats.positions = 0;
      console.log('   ℹ️  Table not found, created empty file');
    }

    // 3. Migrate Orders
    console.log('📊 Migrating orders...');
    if (tableExists(db, 'live_orders')) {
      const orders = db.prepare(`
        SELECT * FROM live_orders ORDER BY created_at DESC LIMIT 10000
      `).all();
      writeJSONL(FILES.ORDERS, orders);
      stats.orders = orders.length;
    } else {
      writeJSONL(FILES.ORDERS, []);
      stats.orders = 0;
      console.log('   ℹ️  Table not found, created empty file');
    }

    // 4. Migrate Trade History
    console.log('📊 Migrating trade history...');
    if (tableExists(db, 'trade_history')) {
      const tradeHistory = db.prepare(`
        SELECT * FROM trade_history ORDER BY trade_time DESC LIMIT 10000
      `).all();
      writeJSONL(FILES.TRADE_HISTORY, tradeHistory);
      stats.trade_history = tradeHistory.length;
    } else {
      writeJSONL(FILES.TRADE_HISTORY, []);
      stats.trade_history = 0;
      console.log('   ℹ️  Table not found, created empty file');
    }

    // 5. Migrate TPSL Configs
    console.log('📊 Migrating TPSL configs...');
    if (tableExists(db, 'position_tpsl_config')) {
      const tpslConfigs = db.prepare(`
        SELECT * FROM position_tpsl_config ORDER BY created_at DESC
      `).all();
      writeJSONL(FILES.TPSL_CONFIG, tpslConfigs);
      stats.tpsl_config = tpslConfigs.length;
    } else {
      writeJSONL(FILES.TPSL_CONFIG, []);
      stats.tpsl_config = 0;
      console.log('   ℹ️  Table not found, created empty file');
    }

    // 6. Migrate Defense Configs
    console.log('📊 Migrating defense configs...');
    if (tableExists(db, 'defense_add_config')) {
      const defenseConfigs = db.prepare(`
        SELECT * FROM defense_add_config ORDER BY created_at DESC
      `).all();
      writeJSONL(FILES.DEFENSE_CONFIG, defenseConfigs);
      stats.defense_config = defenseConfigs.length;
    } else {
      writeJSONL(FILES.DEFENSE_CONFIG, []);
      stats.defense_config = 0;
      console.log('   ℹ️  Table not found, created empty file');
    }

    console.log('\n✅ Migration completed successfully!');
    console.log(`\n📁 Output directory: ${OUTPUT_DIR}`);
    console.log('\n📊 Summary:');
    console.log(`   - Accounts: ${stats.accounts}`);
    console.log(`   - Positions: ${stats.positions}`);
    console.log(`   - Orders: ${stats.orders}`);
    console.log(`   - Trade History: ${stats.trade_history}`);
    console.log(`   - TPSL Configs: ${stats.tpsl_config}`);
    console.log(`   - Defense Configs: ${stats.defense_config}\n`);

  } catch (error) {
    console.error('\n❌ Migration failed:', error.message);
    console.error(error);
    process.exit(1);
  } finally {
    db.close();
  }
}

// Run migration
migrateDatabase();

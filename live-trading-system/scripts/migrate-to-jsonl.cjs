#!/usr/bin/env node

/**
 * 数据库到JSONL迁移脚本
 * 将SQLite数据库中的实时交易数据迁移到JSONL文件
 */

const Database = require('better-sqlite3');
const fs = require('fs');
const path = require('path');

const DB_PATH = path.join(__dirname, 'trading.db');
const DATA_DIR = path.join(__dirname, 'data', 'trading');

// 确保数据目录存在
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

// 文件路径
const FILES = {
  ACCOUNTS: path.join(DATA_DIR, 'accounts.jsonl'),
  POSITIONS: path.join(DATA_DIR, 'positions.jsonl'),
  ORDERS: path.join(DATA_DIR, 'orders.jsonl'),
  TRADE_HISTORY: path.join(DATA_DIR, 'trade_history.jsonl'),
  TPSL_CONFIG: path.join(DATA_DIR, 'tpsl_config.jsonl'),
  DEFENSE_CONFIG: path.join(DATA_DIR, 'defense_config.jsonl'),
};

/**
 * 写入JSONL文件
 */
function writeJSONL(filePath, records) {
  const content = records.map(r => JSON.stringify(r)).join('\n') + '\n';
  fs.writeFileSync(filePath, content, 'utf8');
  console.log(`✅ 写入 ${records.length} 条记录到 ${path.basename(filePath)}`);
}

/**
 * 迁移数据
 */
function migrateData() {
  console.log('🚀 开始迁移数据库到JSONL...\n');

  // 检查数据库文件是否存在
  if (!fs.existsSync(DB_PATH)) {
    console.log('⚠️  数据库文件不存在，创建空的JSONL文件');
    Object.values(FILES).forEach(file => {
      fs.writeFileSync(file, '', 'utf8');
    });
    console.log('✅ 创建完成');
    return;
  }

  const db = new Database(DB_PATH, { readonly: true });

  try {
    // 1. 迁移账户
    console.log('📋 迁移账户数据...');
    try {
      const accounts = db.prepare(`
        SELECT * FROM live_trading_accounts ORDER BY created_at DESC
      `).all();
      writeJSONL(FILES.ACCOUNTS, accounts);
    } catch (error) {
      console.log('⚠️  账户表不存在或为空');
      fs.writeFileSync(FILES.ACCOUNTS, '', 'utf8');
    }

    // 2. 迁移持仓
    console.log('📋 迁移持仓数据...');
    try {
      const positions = db.prepare(`
        SELECT * FROM live_positions ORDER BY created_at DESC
      `).all();
      writeJSONL(FILES.POSITIONS, positions);
    } catch (error) {
      console.log('⚠️  持仓表不存在或为空');
      fs.writeFileSync(FILES.POSITIONS, '', 'utf8');
    }

    // 3. 迁移订单
    console.log('📋 迁移订单数据...');
    try {
      const orders = db.prepare(`
        SELECT * FROM live_orders ORDER BY created_at DESC
      `).all();
      writeJSONL(FILES.ORDERS, orders);
    } catch (error) {
      console.log('⚠️  订单表不存在或为空');
      fs.writeFileSync(FILES.ORDERS, '', 'utf8');
    }

    // 4. 迁移交易历史
    console.log('📋 迁移交易历史...');
    try {
      const history = db.prepare(`
        SELECT * FROM trade_history ORDER BY trade_time DESC LIMIT 10000
      `).all();
      writeJSONL(FILES.TRADE_HISTORY, history);
    } catch (error) {
      console.log('⚠️  交易历史表不存在或为空');
      fs.writeFileSync(FILES.TRADE_HISTORY, '', 'utf8');
    }

    // 5. 迁移TP/SL配置
    console.log('📋 迁移TP/SL配置...');
    try {
      const tpslConfig = db.prepare(`
        SELECT * FROM position_tpsl_config ORDER BY created_at DESC
      `).all();
      writeJSONL(FILES.TPSL_CONFIG, tpslConfig);
    } catch (error) {
      console.log('⚠️  TP/SL配置表不存在或为空');
      fs.writeFileSync(FILES.TPSL_CONFIG, '', 'utf8');
    }

    // 6. 迁移防守加仓配置
    console.log('📋 迁移防守加仓配置...');
    try {
      const defenseConfig = db.prepare(`
        SELECT * FROM defense_add_config ORDER BY created_at DESC
      `).all();
      writeJSONL(FILES.DEFENSE_CONFIG, defenseConfig);
    } catch (error) {
      console.log('⚠️  防守加仓配置表不存在或为空');
      fs.writeFileSync(FILES.DEFENSE_CONFIG, '', 'utf8');
    }

    console.log('\n✅ 数据迁移完成！');
    console.log('\n📊 统计信息:');
    Object.entries(FILES).forEach(([name, file]) => {
      if (fs.existsSync(file)) {
        const lines = fs.readFileSync(file, 'utf8').split('\n').filter(l => l.trim()).length;
        console.log(`  ${name}: ${lines} 条记录`);
      }
    });

    console.log('\n💡 提示:');
    console.log('  1. JSONL文件位于: ' + DATA_DIR);
    console.log('  2. 原数据库文件未被修改');
    console.log('  3. 可以设置环境变量 STORAGE_MODE=jsonl 来使用JSONL存储');
    console.log('  4. 备份建议: 定期备份 data/trading 目录');

  } catch (error) {
    console.error('❌ 迁移失败:', error.message);
    process.exit(1);
  } finally {
    db.close();
  }
}

// 执行迁移
if (require.main === module) {
  migrateData();
}

module.exports = { migrateData };

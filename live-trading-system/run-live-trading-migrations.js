import Database from 'better-sqlite3';
import fs from 'fs';

const dbPath = '.wrangler/state/v3/d1/miniflare-D1DatabaseObject/3c9bc9ebbf8d47b6582e4d8b0a036070724f940ae907dc856bcd6db3600bc2d6.sqlite';
const db = new Database(dbPath);

const migrations = [
  '20251110_live_trading_tables.sql',
  '20251110_multi_account_support.sql',
  '20251110_defense_add_config.sql',
  '20251110_position_tpsl_config.sql',
  '20251110_trade_history.sql',
  '20251110_demo_trading.sql',
  '20251110_panic_indicator_history.sql',
  '20251110_add_initial_balance.sql'
];

console.log('🚀 开始运行实盘交易相关迁移...\n');

for (const migrationFile of migrations) {
  const filePath = `./migrations/${migrationFile}`;
  
  if (!fs.existsSync(filePath)) {
    console.log(`⏭️  跳过: ${migrationFile} (文件不存在)`);
    continue;
  }
  
  console.log(`📄 执行: ${migrationFile}`);
  
  try {
    const sql = fs.readFileSync(filePath, 'utf8');
    
    // Split by semicolon and execute each statement
    const statements = sql
      .split(';')
      .map(s => s.trim())
      .filter(s => s && !s.startsWith('--'));
    
    for (const statement of statements) {
      if (statement) {
        db.exec(statement);
      }
    }
    
    console.log(`   ✅ 成功\n`);
  } catch (error) {
    console.log(`   ⚠️  ${error.message}\n`);
  }
}

console.log('🎉 迁移完成！\n');

// Verify tables were created
console.log('📊 验证表创建情况:');
const tables = db.prepare(`
  SELECT name FROM sqlite_master 
  WHERE type='table' AND name IN ('okx_accounts', 'live_positions', 'live_orders', 'defense_add_config')
  ORDER BY name
`).all();

tables.forEach(t => console.log(`   ✓ ${t.name}`));

db.close();

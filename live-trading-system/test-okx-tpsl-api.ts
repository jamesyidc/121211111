/**
 * 测试OKX止盈止损API
 * 
 * 目的：验证为什么只有止损生效，止盈不生效
 * 
 * 假设：
 * 1. OKX可能不支持在同一个API调用中同时设置止盈和止损
 * 2. 需要分开调用两次API
 * 3. 或者参数格式有问题
 */

import { OKXService } from './src/services/okxService';

// 测试数据
const testCases = [
  {
    name: '测试1: 同时设置止盈和止损（当前方法）',
    params: {
      symbol: 'CFX',
      side: 'long' as const,
      takeProfit: { profitRate: 10 },
      stopLoss: { lossRate: 5 }
    }
  },
  {
    name: '测试2: 只设置止盈',
    params: {
      symbol: 'CFX',
      side: 'long' as const,
      takeProfit: { profitRate: 10 }
    }
  },
  {
    name: '测试3: 只设置止损',
    params: {
      symbol: 'CFX',
      side: 'long' as const,
      stopLoss: { lossRate: 5 }
    }
  }
];

async function testOKXTPSL() {
  console.log('🧪 开始测试OKX止盈止损API\n');
  console.log('⚠️  警告: 这将在实际OKX账户上创建订单！\n');
  
  // 从环境变量读取API配置
  const apiKey = process.env.OKX_API_KEY;
  const apiSecret = process.env.OKX_API_SECRET;
  const passphrase = process.env.OKX_PASSPHRASE;
  
  if (!apiKey || !apiSecret || !passphrase) {
    console.error('❌ 缺少OKX API配置');
    console.log('请设置环境变量:');
    console.log('  export OKX_API_KEY=your_key');
    console.log('  export OKX_API_SECRET=your_secret');
    console.log('  export OKX_PASSPHRASE=your_passphrase');
    process.exit(1);
  }
  
  const okx = new OKXService(apiKey, apiSecret, passphrase, false);
  
  try {
    // 1. 查询当前持仓
    console.log('1️⃣ 查询当前持仓...\n');
    const positions = await okx.getPositions('SWAP');
    const cfxPosition = positions.find((p: any) => 
      p.instId === 'CFX-USDT-SWAP' && p.posSide === 'long'
    );
    
    if (!cfxPosition) {
      console.log('❌ 未找到CFX-USDT-SWAP做多持仓');
      console.log('当前持仓:', positions.map((p: any) => 
        `${p.instId} ${p.posSide} (${p.pos}张)`
      ).join(', '));
      process.exit(1);
    }
    
    console.log('✅ 找到持仓:');
    console.log(`   币对: ${cfxPosition.instId}`);
    console.log(`   方向: ${cfxPosition.posSide}`);
    console.log(`   数量: ${cfxPosition.pos}张`);
    console.log(`   开仓均价: ${cfxPosition.avgPx}`);
    console.log(`   未实现盈亏: ${cfxPosition.upl} USDT\n`);
    
    const entryPrice = parseFloat(cfxPosition.avgPx);
    
    // 2. 测试不同的API调用方式
    for (let i = 0; i < testCases.length; i++) {
      const testCase = testCases[i];
      console.log(`\n${'='.repeat(60)}`);
      console.log(`${testCase.name}`);
      console.log('='.repeat(60));
      
      // 计算预期价格
      const tpPrice = testCase.params.takeProfit 
        ? entryPrice * (1 + testCase.params.takeProfit.profitRate / 100)
        : null;
      const slPrice = testCase.params.stopLoss
        ? entryPrice * (1 - testCase.params.stopLoss.lossRate / 100)
        : null;
      
      console.log('\n📊 预期结果:');
      console.log(`   开仓均价: ${entryPrice}`);
      if (tpPrice) console.log(`   止盈价格: ${tpPrice.toFixed(6)} (${testCase.params.takeProfit?.profitRate}%)`);
      if (slPrice) console.log(`   止损价格: ${slPrice.toFixed(6)} (${testCase.params.stopLoss?.lossRate}%)`);
      
      // 取消之前的订单
      console.log('\n🗑️  取消现有止盈止损订单...');
      try {
        const algoOrders = await okx.getPendingOrders('CFX', 'conditional');
        const tpslOrders = algoOrders.filter((order: any) => 
          order.instId === 'CFX-USDT-SWAP' && order.posSide === 'long'
        );
        
        for (const order of tpslOrders) {
          console.log(`   取消订单: ${order.algoId}`);
          await okx.request('POST', '/api/v5/trade/cancel-algos', [{
            instId: order.instId,
            algoId: order.algoId
          }]);
        }
        console.log('   ✅ 已取消所有现有订单');
      } catch (error: any) {
        console.log('   ⚠️  取消订单失败（可能没有现有订单）:', error.message);
      }
      
      // 等待1秒
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // 调用API
      console.log('\n📡 调用OKX API...');
      try {
        const result = await okx.setFullTPSL(testCase.params);
        console.log('✅ API调用成功!');
        console.log('响应:', JSON.stringify(result, null, 2));
      } catch (error: any) {
        console.log('❌ API调用失败:', error.message);
        if (error.response) {
          console.log('错误详情:', error.response);
        }
      }
      
      // 等待2秒让订单生效
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // 验证订单是否创建成功
      console.log('\n🔍 验证订单状态...');
      try {
        const algoOrders = await okx.getPendingOrders('CFX', 'conditional');
        const tpslOrders = algoOrders.filter((order: any) => 
          order.instId === 'CFX-USDT-SWAP' && order.posSide === 'long'
        );
        
        console.log(`   找到 ${tpslOrders.length} 个止盈止损订单:`);
        
        let hasTP = false;
        let hasSL = false;
        
        tpslOrders.forEach((order: any, index: number) => {
          console.log(`\n   订单 ${index + 1}:`);
          console.log(`     订单ID: ${order.algoId}`);
          console.log(`     订单类型: ${order.ordType}`);
          console.log(`     状态: ${order.state}`);
          
          if (order.tpTriggerPx && order.tpTriggerPx !== '') {
            console.log(`     ✅ 止盈触发价: ${order.tpTriggerPx}`);
            hasTP = true;
          }
          
          if (order.slTriggerPx && order.slTriggerPx !== '') {
            console.log(`     ✅ 止损触发价: ${order.slTriggerPx}`);
            hasSL = true;
          }
        });
        
        console.log('\n📋 总结:');
        console.log(`   ${hasTP ? '✅' : '❌'} 止盈订单已创建`);
        console.log(`   ${hasSL ? '✅' : '❌'} 止损订单已创建`);
        
        if (testCase.params.takeProfit && !hasTP) {
          console.log('\n⚠️  警告: 设置了止盈但订单中没有止盈！');
        }
        
        if (testCase.params.stopLoss && !hasSL) {
          console.log('\n⚠️  警告: 设置了止损但订单中没有止损！');
        }
        
      } catch (error: any) {
        console.log('❌ 查询订单失败:', error.message);
      }
      
      // 如果不是最后一个测试，询问是否继续
      if (i < testCases.length - 1) {
        console.log('\n⏸️  按回车继续下一个测试...');
        await new Promise(resolve => {
          process.stdin.once('data', resolve);
        });
      }
    }
    
    console.log('\n\n✅ 所有测试完成！');
    console.log('\n💡 建议:');
    console.log('1. 检查OKX App，查看实际显示的止盈止损');
    console.log('2. 对比不同测试方法的效果');
    console.log('3. 如果同时设置不生效，可能需要分开调用两次API');
    
  } catch (error: any) {
    console.error('\n❌ 测试失败:', error.message);
    if (error.stack) {
      console.error(error.stack);
    }
  }
}

// 运行测试
if (require.main === module) {
  testOKXTPSL()
    .then(() => process.exit(0))
    .catch((error) => {
      console.error('Fatal error:', error);
      process.exit(1);
    });
}

export { testOKXTPSL };

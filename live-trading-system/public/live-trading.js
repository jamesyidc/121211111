// OKX实盘交易前端脚本

const SYMBOLS = [
  'BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'LTC', 'DOGE', 'SUI', 'TRX', 'TON',
  'ETC', 'BCH', 'HBAR', 'XLM', 'FIL', 'ADA', 'LINK', 'CRO', 'DOT', 'UNI',
  'NEAR', 'APT', 'CFX', 'CRV', 'STX', 'LDO', 'TAO'
];

let currentLimitSide = 'buy';
let currentMarketSide = 'buy';
let availableBalance = 0;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
  initializeSymbolSelects();
  loadAccountInfo();
  loadPositions();
  loadConfig();
  
  // 自动刷新
  setInterval(() => {
    loadAccountInfo();
    loadPositions();
  }, 30000); // 30秒刷新一次
});

// 初始化交易对选择框
function initializeSymbolSelects() {
  const limitSelect = document.getElementById('limitSymbol');
  const marketSelect = document.getElementById('marketSymbol');
  
  SYMBOLS.forEach(symbol => {
    const option1 = document.createElement('option');
    option1.value = symbol;
    option1.textContent = `${symbol}/USDT`;
    limitSelect.appendChild(option1);
    
    const option2 = document.createElement('option');
    option2.value = symbol;
    option2.textContent = `${symbol}/USDT`;
    marketSelect.appendChild(option2);
  });
}

// 切换标签页
function switchTab(tab) {
  // 隐藏所有面板
  ['order', 'positions', 'history', 'config'].forEach(t => {
    document.getElementById(`panel-${t}`).classList.add('hidden');
    document.getElementById(`tab-${t}`).classList.remove('tab-active');
    document.getElementById(`tab-${t}`).classList.add('tab-inactive');
  });
  
  // 显示选中的面板
  document.getElementById(`panel-${tab}`).classList.remove('hidden');
  document.getElementById(`tab-${tab}`).classList.add('tab-active');
  document.getElementById(`tab-${tab}`).classList.remove('tab-inactive');
  
  // 加载对应数据
  if (tab === 'positions') {
    loadPositions();
  } else if (tab === 'history') {
    loadHistory();
  } else if (tab === 'config') {
    loadConfig();
  }
}

// 加载账户信息
async function loadAccountInfo() {
  try {
    const response = await fetch('/api/live-trading/account');
    const data = await response.json();
    
    if (data.success) {
      const account = data.account;
      document.getElementById('totalEquity').textContent = `${account.totalEquity.toFixed(2)} USDT`;
      document.getElementById('availableBalance').textContent = `${account.availableBalance.toFixed(2)} USDT`;
      document.getElementById('unrealizedPnl').textContent = `${account.unrealizedPnl >= 0 ? '+' : ''}${account.unrealizedPnl.toFixed(2)} USDT`;
      document.getElementById('realizedPnl').textContent = `${account.realizedPnl >= 0 ? '+' : ''}${account.realizedPnl.toFixed(2)} USDT`;
      
      availableBalance = account.availableBalance;
      
      // 设置颜色
      document.getElementById('unrealizedPnl').className = account.unrealizedPnl >= 0 ? 'text-2xl font-bold text-green-600' : 'text-2xl font-bold text-red-600';
      document.getElementById('realizedPnl').className = account.realizedPnl >= 0 ? 'text-2xl font-bold text-green-600' : 'text-2xl font-bold text-red-600';
    }
  } catch (error) {
    console.error('加载账户信息失败:', error);
  }
}

// 限价单：设置方向
function setLimitSide(side) {
  currentLimitSide = side;
  const buyBtn = document.getElementById('limit-buy');
  const sellBtn = document.getElementById('limit-sell');
  
  if (side === 'buy') {
    buyBtn.className = 'flex-1 py-2 rounded bg-green-500 text-white hover:bg-green-600';
    sellBtn.className = 'flex-1 py-2 rounded bg-gray-300 hover:bg-gray-400';
  } else {
    buyBtn.className = 'flex-1 py-2 rounded bg-gray-300 hover:bg-gray-400';
    sellBtn.className = 'flex-1 py-2 rounded bg-red-500 text-white hover:bg-red-600';
  }
}

// 限价单：设置杠杆
function setLimitLeverage(leverage) {
  document.getElementById('limitLeverage').value = leverage;
  
  // 更新按钮样式
  const buttons = document.querySelectorAll('#panel-order .border:nth-child(1) .flex.gap-2 button');
  buttons.forEach(btn => {
    btn.className = btn.textContent.includes(`${leverage}x`) 
      ? 'flex-1 py-2 rounded bg-blue-500 text-white'
      : 'flex-1 py-2 rounded bg-gray-200 hover:bg-gray-300';
  });
}

// 限价单：设置百分比
function setLimitPercentage(percentage) {
  const amount = (availableBalance * percentage / 100).toFixed(2);
  document.getElementById('limitAmount').value = amount;
}

// 市价单：设置方向
function setMarketSide(side) {
  currentMarketSide = side;
  const buyBtn = document.getElementById('market-buy');
  const sellBtn = document.getElementById('market-sell');
  
  if (side === 'buy') {
    buyBtn.className = 'flex-1 py-2 rounded bg-green-500 text-white hover:bg-green-600';
    sellBtn.className = 'flex-1 py-2 rounded bg-gray-300 hover:bg-gray-400';
  } else {
    buyBtn.className = 'flex-1 py-2 rounded bg-gray-300 hover:bg-gray-400';
    sellBtn.className = 'flex-1 py-2 rounded bg-red-500 text-white hover:bg-red-600';
  }
}

// 市价单：设置杠杆
function setMarketLeverage(leverage) {
  document.getElementById('marketLeverage').value = leverage;
  
  // 更新按钮样式
  const buttons = document.querySelectorAll('#panel-order .border:nth-child(2) .flex.gap-2 button');
  buttons.forEach(btn => {
    btn.className = btn.textContent.includes(`${leverage}x`)
      ? 'flex-1 py-2 rounded bg-blue-500 text-white'
      : 'flex-1 py-2 rounded bg-gray-200 hover:bg-gray-300';
  });
}

// 市价单：设置百分比
function setMarketPercentage(percentage) {
  const amount = (availableBalance * percentage / 100).toFixed(2);
  document.getElementById('marketAmount').value = amount;
}

// 提交限价单
async function submitLimitOrder() {
  const symbol = document.getElementById('limitSymbol').value;
  const priceType = document.getElementById('limitPriceType').value;
  const leverage = parseInt(document.getElementById('limitLeverage').value);
  const amount = parseFloat(document.getElementById('limitAmount').value);
  
  if (!amount || amount <= 0) {
    alert('请输入有效的USDT数量');
    return;
  }
  
  if (confirm(`确认提交限价单？\n币种: ${symbol}\n方向: ${currentLimitSide === 'buy' ? '做多' : '做空'}\n价格: ${priceType}\n杠杆: ${leverage}x\n数量: ${amount} USDT`)) {
    try {
      const response = await fetch('/api/live-trading/order/limit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol,
          side: currentLimitSide,
          priceType,
          leverage,
          usdtAmount: amount
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        alert('限价单提交成功！');
        document.getElementById('limitAmount').value = '';
        loadAccountInfo();
        loadPositions();
      } else {
        alert(`提交失败: ${data.error}`);
      }
    } catch (error) {
      alert(`提交失败: ${error.message}`);
    }
  }
}

// 提交市价单
async function submitMarketOrder() {
  const symbol = document.getElementById('marketSymbol').value;
  const leverage = parseInt(document.getElementById('marketLeverage').value);
  const amount = parseFloat(document.getElementById('marketAmount').value);
  
  if (!amount || amount <= 0) {
    alert('请输入有效的USDT数量');
    return;
  }
  
  if (confirm(`确认提交市价单？\n币种: ${symbol}\n方向: ${currentMarketSide === 'buy' ? '做多' : '做空'}\n杠杆: ${leverage}x\n数量: ${amount} USDT`)) {
    try {
      const response = await fetch('/api/live-trading/order/market', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol,
          side: currentMarketSide,
          leverage,
          usdtAmount: amount
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        alert('市价单提交成功！');
        document.getElementById('marketAmount').value = '';
        loadAccountInfo();
        loadPositions();
      } else {
        alert(`提交失败: ${data.error}`);
      }
    } catch (error) {
      alert(`提交失败: ${error.message}`);
    }
  }
}

// 加载持仓
async function loadPositions() {
  try {
    const response = await fetch('/api/live-trading/positions');
    const data = await response.json();
    
    if (data.success) {
      const container = document.getElementById('positionsList');
      
      if (data.positions.length === 0) {
        container.innerHTML = '<p class="text-gray-500 text-center py-8">暂无持仓</p>';
        return;
      }
      
      container.innerHTML = data.positions.map(pos => `
        <div class="position-card position-${pos.side}">
          <div class="flex justify-between items-start mb-3">
            <div>
              <h3 class="text-xl font-bold">${pos.symbol}/USDT</h3>
              <span class="inline-block px-2 py-1 rounded text-sm ${pos.side === 'long' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
                ${pos.side === 'long' ? '做多' : '做空'} ${pos.leverage}x
              </span>
            </div>
            <div class="text-right">
              <p class="text-2xl font-bold ${pos.pnl >= 0 ? 'text-green-600' : 'text-red-600'}">
                ${pos.pnl >= 0 ? '+' : ''}${pos.pnl.toFixed(2)} USDT
              </p>
              <p class="text-sm ${pos.pnlRate >= 0 ? 'text-green-600' : 'text-red-600'}">
                ${pos.pnlRate >= 0 ? '+' : ''}${pos.pnlRate.toFixed(2)}%
              </p>
            </div>
          </div>
          
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
            <div>
              <p class="text-xs text-gray-500">开仓价</p>
              <p class="font-semibold">${pos.entryPrice}</p>
            </div>
            <div>
              <p class="text-xs text-gray-500">当前价</p>
              <p class="font-semibold">${pos.currentPrice}</p>
            </div>
            <div>
              <p class="text-xs text-gray-500">仓位</p>
              <p class="font-semibold">${pos.size}</p>
            </div>
            <div>
              <p class="text-xs text-gray-500">保证金</p>
              <p class="font-semibold">${pos.usdtAmount} USDT</p>
            </div>
          </div>
          
          ${pos.tpPrice || pos.slPrice ? `
          <div class="bg-gray-50 rounded p-2 mb-3 text-sm">
            ${pos.tpPrice ? `<p class="text-green-600">止盈: ${pos.tpPrice} (${pos.tpRate}%)</p>` : ''}
            ${pos.slPrice ? `<p class="text-red-600">止损: ${pos.slPrice} (${pos.slRate}%)</p>` : ''}
          </div>
          ` : ''}
          
          ${pos.maxHoldingCandles ? `
          <div class="bg-blue-50 rounded p-2 mb-3 text-sm">
            <p class="text-blue-600">
              持仓周期: ${pos.currentHoldingCandles}/${pos.maxHoldingCandles} 根 (${pos.candleInterval})
            </p>
          </div>
          ` : ''}
          
          <div class="flex gap-2">
            <button onclick="showTPSLModal(${pos.id})" class="flex-1 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
              <i class="fas fa-crosshairs"></i> 设置止盈止损
            </button>
            <button onclick="closePosition(${pos.id})" class="flex-1 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600">
              <i class="fas fa-times-circle"></i> 平仓
            </button>
          </div>
        </div>
      `).join('');
    }
  } catch (error) {
    console.error('加载持仓失败:', error);
  }
}

// 显示止盈止损设置模态框
function showTPSLModal(positionId) {
  // TODO: 实现止盈止损设置模态框
  alert('止盈止损设置功能开发中...');
}

// 平仓
async function closePosition(positionId) {
  if (confirm('确认要平仓吗？')) {
    try {
      const response = await fetch(`/api/live-trading/position/${positionId}/close`, {
        method: 'POST'
      });
      
      const data = await response.json();
      
      if (data.success) {
        alert('平仓成功！');
        loadAccountInfo();
        loadPositions();
      } else {
        alert(`平仓失败: ${data.error}`);
      }
    } catch (error) {
      alert(`平仓失败: ${error.message}`);
    }
  }
}

// 加载历史记录
async function loadHistory() {
  try {
    const response = await fetch('/api/live-trading/history');
    const data = await response.json();
    
    if (data.success) {
      const tbody = document.getElementById('historyTable');
      
      if (data.history.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center py-8 text-gray-500">暂无历史记录</td></tr>';
        return;
      }
      
      tbody.innerHTML = data.history.map(h => `
        <tr class="border-b hover:bg-gray-50">
          <td class="px-4 py-2">${new Date(h.exitTime).toLocaleString()}</td>
          <td class="px-4 py-2 font-semibold">${h.symbol}</td>
          <td class="px-4 py-2">
            <span class="px-2 py-1 rounded text-sm ${h.side === 'long' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
              ${h.side === 'long' ? '做多' : '做空'}
            </span>
          </td>
          <td class="px-4 py-2 text-right">${h.entryPrice}</td>
          <td class="px-4 py-2 text-right">${h.exitPrice}</td>
          <td class="px-4 py-2 text-right font-bold ${h.pnl >= 0 ? 'text-green-600' : 'text-red-600'}">
            ${h.pnl >= 0 ? '+' : ''}${h.pnl.toFixed(2)}
          </td>
          <td class="px-4 py-2 text-right font-bold ${h.pnlRate >= 0 ? 'text-green-600' : 'text-red-600'}">
            ${h.pnlRate >= 0 ? '+' : ''}${h.pnlRate.toFixed(2)}%
          </td>
        </tr>
      `).join('');
    }
  } catch (error) {
    console.error('加载历史记录失败:', error);
  }
}

// 加载配置
async function loadConfig() {
  try {
    const response = await fetch('/api/live-trading/config');
    const data = await response.json();
    
    if (data.success && data.config) {
      document.getElementById('apiKey').value = data.config.apiKey || '';
      document.getElementById('apiSecret').value = data.config.apiSecret || '';
      document.getElementById('passphrase').value = data.config.passphrase || '';
      document.getElementById('isTestnet').checked = data.config.isTestnet || false;
    }
  } catch (error) {
    console.error('加载配置失败:', error);
  }
}

// 保存配置
async function saveConfig() {
  const config = {
    apiKey: document.getElementById('apiKey').value,
    apiSecret: document.getElementById('apiSecret').value,
    passphrase: document.getElementById('passphrase').value,
    isTestnet: document.getElementById('isTestnet').checked
  };
  
  if (!config.apiKey || !config.apiSecret || !config.passphrase) {
    alert('请填写完整的API配置信息');
    return;
  }
  
  try {
    const response = await fetch('/api/live-trading/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    
    const data = await response.json();
    
    if (data.success) {
      alert('配置保存成功！');
      loadAccountInfo();
    } else {
      alert(`保存失败: ${data.error}`);
    }
  } catch (error) {
    alert(`保存失败: ${error.message}`);
  }
}

// 刷新数据
function refreshData() {
  loadAccountInfo();
  loadPositions();
  loadHistory();
}

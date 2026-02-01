// OKX实盘交易系统 V2 - 多账户版本

const SYMBOLS = [
  'BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'LTC', 'DOGE', 'SUI', 'TRX', 'TON',
  'ETC', 'BCH', 'HBAR', 'XLM', 'FIL', 'ADA', 'LINK', 'CRO', 'DOT', 'UNI',
  'NEAR', 'APT', 'CFX', 'CRV', 'STX', 'LDO', 'TAO'
];

let state = {
  currentSymbol: 'BTC',
  orderType: 'limit',
  side: 'buy',
  leverage: 10,
  currentAccountId: null,
  accounts: [],
  availableBalance: 0,
  positions: [] // 保存持仓数据
};

// 初始化
document.addEventListener('DOMContentLoaded', function() {
  loadAccounts();
  initializeSymbolList();
  initializeEventListeners();
  
  // 定时刷新
  setInterval(() => {
    if (state.currentAccountId) {
      loadAccountInfo();
      loadPositions();
      updatePrice();
    }
  }, 10000); // 10秒刷新一次
});

// 加载账户列表
async function loadAccounts() {
  try {
    console.log('loadAccounts: Fetching accounts list...');
    const response = await fetch('/api/debug2/accounts/list');
    const data = await response.json();
    
    console.log('loadAccounts response:', data);
    
    if (data.success) {
      state.accounts = data.accounts || [];
      console.log('loadAccounts: Found', state.accounts.length, 'accounts');
      
      // 设置当前账户（默认选择第一个或上次使用的）
      const savedAccountId = localStorage.getItem('currentAccountId');
      console.log('💾 Saved account ID from localStorage:', savedAccountId);
      
      const accountExists = savedAccountId && state.accounts.find(a => a.id == savedAccountId);
      console.log('✅ Account exists in database:', accountExists ? 'Yes' : 'No');
      
      if (accountExists) {
        state.currentAccountId = savedAccountId;  // 保持字符串类型
        console.log('📌 Using saved account:', savedAccountId);
      } else if (state.accounts.length > 0) {
        state.currentAccountId = state.accounts[0].id;
        console.log('📌 Using first account (saved not found):', state.currentAccountId);
        // 清除无效的保存记录
        if (savedAccountId) {
          console.warn('⚠️ Clearing invalid saved account ID:', savedAccountId);
          localStorage.removeItem('currentAccountId');
        }
      } else {
        console.warn('⚠️ No accounts available');
      }
      
      updateAccountDisplay();
      
      // 如果没有账户，显示提示横幅
      if (state.accounts.length === 0) {
        const banner = document.getElementById('noAccountBanner');
        if (banner) banner.style.display = 'block';
      } else {
        const banner = document.getElementById('noAccountBanner');
        if (banner) banner.style.display = 'none';
      }
      
      if (state.currentAccountId) {
        loadAccountInfo();
        loadPositions();
      }
    }
  } catch (error) {
    console.error('加载账户列表失败:', error);
  }
}

// 更新账户显示
function updateAccountDisplay() {
  const account = state.accounts.find(a => a.id === state.currentAccountId);
  const accountName = document.getElementById('currentAccountName');
  const accountStatus = document.getElementById('accountStatus');
  const quickAddBtn = document.getElementById('quickAddAccountBtn');
  const accountSelector = document.getElementById('accountSelector');
  
  if (account) {
    accountName.textContent = account.account_name || account.name || '未命名';
    // ✅ 新表没有 is_active 字段，默认显示为在线
    accountStatus.className = 'account-status-online';
    localStorage.setItem('currentAccountId', account.id);
    
    // 隐藏快捷添加按钮
    if (quickAddBtn) quickAddBtn.style.display = 'none';
    if (accountSelector) accountSelector.style.display = 'flex';
  } else {
    accountName.textContent = '未配置';
    accountStatus.className = 'account-status-offline';
    
    // 显示快捷添加按钮
    if (quickAddBtn) quickAddBtn.style.display = 'block';
    if (state.accounts.length === 0 && accountSelector) {
      accountSelector.style.display = 'none';
    }
  }
}

// 初始化交易对列表
function initializeSymbolList() {
  const container = document.getElementById('symbolList');
  
  container.innerHTML = SYMBOLS.map((symbol, index) => `
    <div 
      class="symbol-item ${index === 0 ? 'active' : ''}" 
      onclick="selectSymbol('${symbol}')"
      data-symbol="${symbol}"
    >
      <div class="flex justify-between items-center">
        <div>
          <div class="font-semibold">${symbol}/USDT</div>
          <div class="text-xs text-gray-500">永续</div>
        </div>
        <div class="text-right">
          <div class="text-sm font-semibold" id="price-${symbol}">--</div>
          <div class="text-xs" id="change-${symbol}">--</div>
        </div>
      </div>
    </div>
  `).join('');
}

// 初始化事件监听
function initializeEventListeners() {
  // 搜索框
  document.getElementById('symbolSearch').addEventListener('input', function(e) {
    const searchTerm = e.target.value.toUpperCase();
    const items = document.querySelectorAll('.symbol-item');
    
    items.forEach(item => {
      const symbol = item.dataset.symbol;
      if (symbol.includes(searchTerm)) {
        item.style.display = 'block';
      } else {
        item.style.display = 'none';
      }
    });
  });

  // 账户表单提交
  document.getElementById('accountForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    await saveAccount();
  });
}

// 选择交易对
function selectSymbol(symbol) {
  state.currentSymbol = symbol;
  
  // 更新UI
  document.querySelectorAll('.symbol-item').forEach(item => {
    item.classList.remove('active');
    if (item.dataset.symbol === symbol) {
      item.classList.add('active');
    }
  });
  
  document.getElementById('currentSymbol').textContent = `${symbol}-USDT`;
  updatePrice();
}

// 更新价格
async function updatePrice() {
  if (!state.currentAccountId) return;
  
  try {
    const response = await fetch(`/api/debug2/ticker/${state.currentSymbol}?accountId=${state.currentAccountId}`);
    const data = await response.json();
    
    if (data.success && data.ticker) {
      const price = parseFloat(data.ticker.last);
      const change = parseFloat(data.ticker.changePercent);
      
      document.getElementById('currentPrice').textContent = price.toFixed(2);
      document.getElementById('priceChange').textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
      document.getElementById('priceChange').className = change >= 0 ? 'text-sm text-green-600' : 'text-sm text-red-600';
    }
  } catch (error) {
    console.error('更新价格失败:', error);
  }
}

// 设置订单类型
function setOrderType(type) {
  state.orderType = type;
  
  if (type === 'limit') {
    document.getElementById('limitOrderPanel').style.display = 'block';
    document.getElementById('marketOrderPanel').style.display = 'none';
    document.getElementById('limitBtn').className = 'flex-1 py-3 rounded-lg font-semibold transition-all bg-blue-500 text-white';
    document.getElementById('marketBtn').className = 'flex-1 py-3 rounded-lg font-semibold transition-all bg-gray-100 text-gray-600';
  } else {
    document.getElementById('limitOrderPanel').style.display = 'none';
    document.getElementById('marketOrderPanel').style.display = 'block';
    document.getElementById('limitBtn').className = 'flex-1 py-3 rounded-lg font-semibold transition-all bg-gray-100 text-gray-600';
    document.getElementById('marketBtn').className = 'flex-1 py-3 rounded-lg font-semibold transition-all bg-blue-500 text-white';
  }
}

// 设置方向
function setSide(side) {
  state.side = side;
  // 更新按钮样式通过CSS处理
}

// 设置杠杆
function setLeverage(leverage) {
  state.leverage = leverage;
  
  // 更新按钮样式
  [3, 5, 10, 20].forEach(lev => {
    const btn = document.getElementById(`lev${lev}`);
    if (btn) {
      if (lev === leverage) {
        btn.className = 'leverage-btn active';
      } else {
        btn.className = 'leverage-btn';
      }
    }
  });
}

// 处理价格类型变化
function handlePriceTypeChange() {
  const priceType = document.getElementById('priceType').value;
  const customPriceInput = document.getElementById('customPriceInput');
  
  if (priceType === 'custom') {
    customPriceInput.style.display = 'block';
    // 更新参考价格
    updateReferencePrice();
  } else {
    customPriceInput.style.display = 'none';
  }
}

// 更新参考价格
async function updateReferencePrice() {
  if (!state.currentAccountId || !state.currentSymbol) return;
  
  try {
    const response = await fetch(`/api/debug2/ticker/${state.currentSymbol}?accountId=${state.currentAccountId}`);
    const data = await response.json();
    
    if (data.success && data.ticker) {
      document.getElementById('referencePrice').textContent = `${parseFloat(data.ticker.last).toFixed(4)}`;
    }
  } catch (error) {
    console.error('获取参考价格失败:', error);
  }
}

// 设置金额百分比
function setAmountPercent(percent) {
  const amount = (state.availableBalance * percent / 100).toFixed(2);
  const amountInput = state.orderType === 'limit' ? 
    document.getElementById('amount') : 
    document.getElementById('marketAmount');
  
  if (amountInput) {
    amountInput.value = amount;
  }
}

// 加载账户信息
async function loadAccountInfo() {
  if (!state.currentAccountId) {
    console.log('loadAccountInfo: No currentAccountId set');
    return;
  }
  
  try {
    console.log('loadAccountInfo: Fetching account info for accountId:', state.currentAccountId);
    const response = await fetch(`/api/debug2/account?accountId=${state.currentAccountId}`);
    const data = await response.json();
    
    console.log('loadAccountInfo response:', data);
    
    if (data.success && data.account) {
      const account = data.account;
      state.availableBalance = account.availableBalance;
      
      // 初始金额
      document.getElementById('initialBalance').textContent = `${account.initialBalance.toFixed(2)} USDT`;
      
      // 总权益
      document.getElementById('totalEquity').textContent = `${account.totalEquity.toFixed(2)} USDT`;
      
      // 可用余额
      document.getElementById('available').textContent = `${account.availableBalance.toFixed(2)} USDT`;
      document.getElementById('availableBalance').textContent = account.availableBalance.toFixed(2);
      
      // 计算持仓保证金 = 总权益 - 可用余额 - 未实现盈亏
      const unrealizedPnl = account.unrealizedPnl || 0;
      const positionMargin = account.totalEquity - account.availableBalance - unrealizedPnl;
      document.getElementById('positionMargin').textContent = `${positionMargin.toFixed(2)} USDT`;
      
      // 未实现盈亏
      const pnlElement = document.getElementById('unrealizedPnl');
      pnlElement.textContent = `${unrealizedPnl >= 0 ? '+' : ''}${unrealizedPnl.toFixed(2)} USDT`;
      pnlElement.className = unrealizedPnl >= 0 ? 'font-bold text-green-600' : 'font-bold text-red-600';
      
      // 当日盈亏
      const dailyPnl = account.dailyPnl || 0;
      const dailyPnlElement = document.getElementById('dailyPnl');
      dailyPnlElement.textContent = `${dailyPnl >= 0 ? '+' : ''}${dailyPnl.toFixed(2)} USDT`;
      dailyPnlElement.className = dailyPnl >= 0 ? 'font-bold text-green-600' : 'font-bold text-red-600';
    } else {
      console.error('loadAccountInfo failed:', data.error || '未知错误');
      showToast(`加载账户信息失败: ${data.error || '未知错误'}`, 'error');
    }
  } catch (error) {
    console.error('加载账户信息失败:', error);
    showToast(`加载账户信息失败: ${error.message}`, 'error');
  }
}

// 加载持仓
async function loadPositions() {
  if (!state.currentAccountId) return;
  
  try {
    const response = await fetch(`/api/debug2/positions?accountId=${state.currentAccountId}`);
    const data = await response.json();
    
    console.log('🔍 loadPositions response:', data);
    console.log('  - success:', data.success);
    console.log('  - positions:', data.positions);
    console.log('  - positions.length:', data.positions ? data.positions.length : 'N/A');
    
    const container = document.getElementById('positionsList');
    
    if (data.success && data.positions && data.positions.length > 0) {
      // 保存持仓数据到state，供后续使用
      state.positions = data.positions;
      
      container.innerHTML = data.positions.map(pos => {
        // 检查是否有止盈止损配置
        const hasTPSL = pos.tpslConfig && (
          pos.tpslConfig.takeProfitPrice || pos.tpslConfig.takeProfitRate ||
          pos.tpslConfig.stopLossPrice || pos.tpslConfig.stopLossRate ||
          pos.tpslConfig.maxHoldTimeframe
        );
        
        return `
        <div class="border border-gray-200 rounded-lg p-3">
          <div class="flex justify-between items-start mb-2">
            <div>
              <div class="font-semibold">${pos.symbol}</div>
              <div class="text-xs ${pos.side === 'long' ? 'text-green-600' : 'text-red-600'}">
                ${pos.side === 'long' ? '做多' : '做空'}
              </div>
            </div>
            <div class="text-right">
              <div class="font-bold ${pos.pnl >= 0 ? 'text-green-600' : 'text-red-600'}">
                ${pos.pnl >= 0 ? '+' : ''}${pos.pnl.toFixed(2)} USDT
              </div>
              <div class="text-xs">${pos.pnlRate >= 0 ? '+' : ''}${pos.pnlRate.toFixed(2)}%</div>
            </div>
          </div>
          <div class="text-xs text-gray-600 space-y-1">
            <div>开仓: ${pos.entryPrice.toFixed(4)}</div>
            <div>当前: ${pos.currentPrice.toFixed(4)}</div>
            <div>数量: ${pos.size} 张</div>
          </div>
          <div class="mt-2">
            <button 
              class="w-full py-2 text-sm bg-red-500 text-white rounded hover:bg-red-600 font-semibold"
              onclick="closePosition('${pos.id}', '${pos.symbol}', '${pos.side}')"
              title="平仓"
            >
              <i class="fas fa-times-circle"></i> 平仓
            </button>
          </div>
        </div>
        `;
      }).join('');
    } else {
      state.positions = [];
      container.innerHTML = `
        <div class="text-center text-gray-500 py-8">
          <i class="fas fa-inbox text-3xl mb-2"></i>
          <div class="text-sm">暂无持仓</div>
        </div>
      `;
    }
  } catch (error) {
    console.error('加载持仓失败:', error);
  }
}

// 提交订单
async function submitOrder() {
  if (!state.currentAccountId) {
    showToast('请先选择或添加API账户', 'error');
    return;
  }
  
  const amountInput = state.orderType === 'limit' ? 
    document.getElementById('amount') : 
    document.getElementById('marketAmount');
  
  const amount = parseFloat(amountInput.value);
  
  if (!amount || amount <= 0) {
    showToast('请输入有效的数量', 'error');
    return;
  }
  
  if (amount > state.availableBalance) {
    showToast('余额不足', 'error');
    return;
  }
  
  const orderData = {
    accountId: state.currentAccountId,
    symbol: state.currentSymbol,
    side: state.side,
    leverage: state.leverage,
    usdtAmount: amount
  };
  
  // 🆕 读取止盈止损设置
  // 市价委托使用 marketTakeProfitRate 和 marketStopLossRate
  // 限价委托使用 limitTakeProfitRate 和 limitStopLossRate
  const takeProfitRateInput = state.orderType === 'market' 
    ? document.getElementById('marketTakeProfitRate')
    : document.getElementById('limitTakeProfitRate');
  const stopLossRateInput = state.orderType === 'market'
    ? document.getElementById('marketStopLossRate')
    : document.getElementById('limitStopLossRate');
  
  if (takeProfitRateInput && takeProfitRateInput.value) {
    const tpRate = parseFloat(takeProfitRateInput.value);
    if (!isNaN(tpRate) && tpRate > 0) {
      orderData.takeProfitRate = tpRate;
      console.log('✅ 止盈收益率:', tpRate + '%');
    }
  }
  
  if (stopLossRateInput && stopLossRateInput.value) {
    const slRate = parseFloat(stopLossRateInput.value);
    if (!isNaN(slRate) && slRate > 0) {
      orderData.stopLossRate = slRate;
      console.log('✅ 止损亏损率:', slRate + '%');
    }
  }
  
  if (state.orderType === 'limit') {
    const priceType = document.getElementById('priceType').value;
    orderData.priceType = priceType;
    
    // 如果是自定义价格，添加customPrice字段
    if (priceType === 'custom') {
      const customPrice = document.getElementById('customPrice').value;
      if (!customPrice || parseFloat(customPrice) <= 0) {
        showToast('请输入有效的开仓价格', 'error');
        return;
      }
      orderData.customPrice = customPrice;
    }
  }
  
  const endpoint = state.orderType === 'limit' ? 
    '/api/debug2/order/limit' : 
    '/api/debug2/order/market';
  
  // 调试日志：查看发送的数据
  console.log('提交订单数据:', JSON.stringify(orderData, null, 2));
  
  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(orderData)
    });
    
    const data = await response.json();
    
    if (data.success) {
      showToast('订单提交成功！', 'success');
      amountInput.value = '';
      loadAccountInfo();
      loadPositions();
    } else {
      showToast(`订单失败: ${data.error}`, 'error');
    }
  } catch (error) {
    showToast(`订单失败: ${error.message}`, 'error');
  }
}

// 平仓（直接全部平仓）
async function closePosition(positionId, symbol, side) {
  console.log('🔥 closePosition called:', { positionId, symbol, side });
  
  // 确认平仓
  if (!confirm(`确认要平仓 ${symbol} 吗？`)) {
    return;
  }
  
  try {
    // ✅ 修复: 调用正确的debug API endpoint
    const response = await fetch('/api/debug2/position/close', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        account_id: state.currentAccountId,
        symbol: symbol
      })
    });
    
    const data = await response.json();
    console.log('📊 Close position response:', data);
    
    if (data.success) {
      showToast('平仓成功！', 'success');
      loadAccountInfo();
      loadPositions();
    } else {
      showToast(`平仓失败: ${data.error}`, 'error');
    }
  } catch (error) {
    console.error('❌ Close position error:', error);
    showToast(`平仓失败: ${error.message}`, 'error');
  }
}



// ============ 账户管理 ============

// 打开账户管理器
function openAccountManager() {
  renderAccountsList();
  document.getElementById('accountModal').classList.add('active');
}

// 关闭账户管理器
function closeAccountManager() {
  document.getElementById('accountModal').classList.remove('active');
}

// 渲染账户列表
function renderAccountsList() {
  const container = document.getElementById('accountsList');
  
  if (state.accounts.length === 0) {
    container.innerHTML = `
      <div class="text-center py-8 text-gray-500">
        <i class="fas fa-user-slash text-4xl mb-3"></i>
        <div>还没有添加任何账户</div>
        <div class="text-sm">点击下方按钮添加您的第一个API账户</div>
      </div>
    `;
    return;
  }
  
  container.innerHTML = state.accounts.map(account => `
    <div class="account-card ${account.id === state.currentAccountId ? 'active' : ''}" onclick="switchAccount('${account.id}')">
      <div class="flex justify-between items-start mb-2">
        <div class="flex items-center gap-2">
          <span class="account-status-online"></span>
          <div>
            <div class="font-bold">${account.account_name || account.name || 'Unknown'}</div>
            <div class="text-xs text-gray-500">${account.api_key.substring(0, 8)}...</div>
          </div>
        </div>
        <div class="flex gap-2">
          <button 
            class="text-blue-500 hover:text-blue-600"
            onclick="event.stopPropagation(); testAccount('${account.id}')"
            title="测试连接"
          >
            <i class="fas fa-plug"></i>
          </button>
          <button 
            class="text-red-500 hover:text-red-600"
            onclick="event.stopPropagation(); deleteAccount('${account.id}')"
            title="删除账户"
          >
            <i class="fas fa-trash"></i>
          </button>
        </div>
      </div>
      <div class="text-xs text-gray-500">
        ${account.is_testnet ? '🧪 测试网' : '🔴 实盘'} | 
        创建时间: ${new Date(account.created_at).toLocaleDateString('zh-CN', { timeZone: 'Asia/Shanghai' })}
      </div>
    </div>
  `).join('');
}

// 切换账户
async function switchAccount(accountId) {
  state.currentAccountId = accountId;
  updateAccountDisplay();
  closeAccountManager();
  
  // 重新加载数据
  await loadAccountInfo();
  await loadPositions();
  
  showToast('账户切换成功', 'success');
}

// 打开添加账户表单
function openAddAccountForm() {
  closeAccountManager();
  document.getElementById('addAccountModal').classList.add('active');
}

// 关闭添加账户表单
function closeAddAccountForm() {
  document.getElementById('addAccountModal').classList.remove('active');
  document.getElementById('accountForm').reset();
}

// 保存账户
async function saveAccount() {
  // 先读取表单元素确保它们存在
  const accountNameEl = document.getElementById('accountName');
  const apiKeyEl = document.getElementById('apiKey');
  const apiSecretEl = document.getElementById('apiSecret');
  const passphraseEl = document.getElementById('passphrase');
  const isTestnetEl = document.getElementById('isTestnet');
  
  console.log('📋 表单元素检查:');
  console.log('  - accountName存在:', !!accountNameEl, '值:', accountNameEl?.value);
  console.log('  - apiKey存在:', !!apiKeyEl, '值:', apiKeyEl?.value);
  console.log('  - apiSecret存在:', !!apiSecretEl, '值:', apiSecretEl?.value ? '***' : '');
  console.log('  - passphrase存在:', !!passphraseEl, '值:', passphraseEl?.value ? '***' : '');
  console.log('  - isTestnet存在:', !!isTestnetEl, 'checked:', isTestnetEl?.checked);
  
  const accountData = {
    accountName: accountNameEl.value.trim(),
    apiKey: apiKeyEl.value.trim(),
    apiSecret: apiSecretEl.value.trim(),
    passphrase: passphraseEl.value.trim(),
    isTestnet: isTestnetEl.checked
  };
  
  console.log('📤 发送账户数据:', {
    ...accountData,
    apiSecret: accountData.apiSecret ? '***' : '',
    passphrase: accountData.passphrase ? '***' : ''
  });
  console.log('📤 JSON字符串:', JSON.stringify(accountData));
  
  // 前端验证
  if (!accountData.accountName) {
    showToast('请填写账户名称', 'error');
    return;
  }
  if (!accountData.apiKey) {
    showToast('请填写API Key', 'error');
    return;
  }
  if (!accountData.apiSecret) {
    showToast('请填写API Secret', 'error');
    return;
  }
  if (!accountData.passphrase) {
    showToast('请填写Passphrase', 'error');
    return;
  }
  
  try {
    const response = await fetch('/api/debug2/accounts/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(accountData)
    });
    
    const data = await response.json();
    console.log('📥 服务器响应:', data);
    
    if (data.success) {
      showToast('账户添加成功！', 'success');
      closeAddAccountForm();
      await loadAccounts();
      
      // 隐藏提示横幅
      const banner = document.getElementById('noAccountBanner');
      if (banner) banner.style.display = 'none';
      
      openAccountManager();
    } else {
      console.error('❌ 添加失败:', data.error);
      showToast(`添加失败: ${data.error}`, 'error');
    }
  } catch (error) {
    console.error('❌ 请求异常:', error);
    showToast(`添加失败: ${error.message}`, 'error');
  }
}

// 测试API连接
async function testAPIConnection() {
  const apiKey = document.getElementById('apiKey').value;
  const apiSecret = document.getElementById('apiSecret').value;
  const passphrase = document.getElementById('passphrase').value;
  const isTestnet = document.getElementById('isTestnet').checked;
  
  if (!apiKey || !apiSecret || !passphrase) {
    showToast('请填写完整的API信息', 'error');
    return;
  }
  
  showToast('正在测试连接...', 'info');
  
  try {
    const response = await fetch('/api/debug2/test-connection', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ apiKey, apiSecret, passphrase, isTestnet })
    });
    
    const data = await response.json();
    
    if (data.success) {
      showToast(`✅ 连接成功！账户余额: ${data.balance} USDT`, 'success');
    } else {
      showToast(`❌ 连接失败: ${data.error}`, 'error');
    }
  } catch (error) {
    showToast(`❌ 连接失败: ${error.message}`, 'error');
  }
}

// 测试已有账户
async function testAccount(accountId) {
  showToast('正在测试连接...', 'info');
  
  try {
    const response = await fetch('/api/debug2/test-connection', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ account_id: accountId })
    });
    const data = await response.json();
    
    if (data.success) {
      showToast(`✅ 连接成功！账户余额: ${data.balance} USDT`, 'success');
      await loadAccounts();
      renderAccountsList();
    } else {
      showToast(`❌ 连接失败: ${data.error}`, 'error');
    }
  } catch (error) {
    showToast(`❌ 连接失败: ${error.message}`, 'error');
  }
}

// 删除账户
async function deleteAccount(accountId) {
  if (!confirm('确认要删除这个账户吗？此操作不可恢复！')) return;
  
  try {
    const response = await fetch(`/api/debug2/accounts/${accountId}`, {
      method: 'DELETE'
    });
    
    const data = await response.json();
    
    if (data.success) {
      showToast('账户已删除', 'success');
      
      if (state.currentAccountId === accountId) {
        state.currentAccountId = null;
      }
      
      await loadAccounts();
      renderAccountsList();
    } else {
      showToast(`删除失败: ${data.error}`, 'error');
    }
  } catch (error) {
    showToast(`删除失败: ${error.message}`, 'error');
  }
}

// ============ 工具函数 ============

// 显示提示消息
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = 'toast';
  
  const icons = {
    success: '<i class="fas fa-check-circle text-green-500"></i>',
    error: '<i class="fas fa-exclamation-circle text-red-500"></i>',
    info: '<i class="fas fa-info-circle text-blue-500"></i>'
  };
  
  toast.innerHTML = `
    <div class="flex items-center gap-3">
      ${icons[type]}
      <div>${message}</div>
    </div>
  `;
  
  document.body.appendChild(toast);
  
  setTimeout(() => {
    toast.style.animation = 'slideIn 0.3s ease-out reverse';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// ========== 止盈止损功能 ==========

function openTPSLModal(positionId, symbol, side) {
  document.getElementById('tpslPositionId').value = positionId;
  document.getElementById('tpslSymbol').value = symbol;
  document.getElementById('tpslSide').value = side;
  
  // 查找该持仓的配置
  const position = state.positions.find(p => p.id === positionId);
  const config = position?.tpslConfig;
  
  // 重置表单
  document.getElementById('tpslForm').reset();
  
  // 如果有已保存的配置，预填充表单
  if (config) {
    // 止盈设置
    if (config.takeProfitPrice || config.takeProfitRate) {
      document.getElementById('enableTP').checked = true;
      document.getElementById('tpSettings').style.display = 'block';
      
      if (config.takeProfitPrice) {
        document.getElementById('takeProfitPrice').value = config.takeProfitPrice;
      }
      if (config.takeProfitRate) {
        document.getElementById('takeProfitRate').value = config.takeProfitRate;
      }
    } else {
      document.getElementById('tpSettings').style.display = 'none';
    }
    
    // 止损设置
    if (config.stopLossPrice || config.stopLossRate) {
      document.getElementById('enableSL').checked = true;
      document.getElementById('slSettings').style.display = 'block';
      
      if (config.stopLossPrice) {
        document.getElementById('stopLossPrice').value = config.stopLossPrice;
      }
      if (config.stopLossRate) {
        document.getElementById('stopLossRate').value = config.stopLossRate;
      }
    } else {
      document.getElementById('slSettings').style.display = 'none';
    }
    
    // 最大持有周期设置
    if (config.maxHoldTimeframe && config.maxHoldBars) {
      document.getElementById('enableMaxHold').checked = true;
      document.getElementById('maxHoldSettings').style.display = 'block';
      document.getElementById('maxHoldTimeframe').value = config.maxHoldTimeframe;
      document.getElementById('maxHoldBars').value = config.maxHoldBars;
    } else {
      document.getElementById('maxHoldSettings').style.display = 'none';
    }
  } else {
    // 没有配置，隐藏所有设置区域
    document.getElementById('tpSettings').style.display = 'none';
    document.getElementById('slSettings').style.display = 'none';
    document.getElementById('maxHoldSettings').style.display = 'none';
  }
  
  document.getElementById('tpslModal').classList.add('active');
}

function closeTPSLModal() {
  document.getElementById('tpslModal').classList.remove('active');
}

// 监听复选框变化，显示/隐藏对应设置
document.addEventListener('DOMContentLoaded', function() {
  const enableTP = document.getElementById('enableTP');
  const enableSL = document.getElementById('enableSL');
  const enableMaxHold = document.getElementById('enableMaxHold');
  
  if (enableTP) {
    enableTP.addEventListener('change', function() {
      document.getElementById('tpSettings').style.display = this.checked ? 'block' : 'none';
    });
  }
  
  if (enableSL) {
    enableSL.addEventListener('change', function() {
      document.getElementById('slSettings').style.display = this.checked ? 'block' : 'none';
    });
  }
  
  if (enableMaxHold) {
    enableMaxHold.addEventListener('change', function() {
      document.getElementById('maxHoldSettings').style.display = this.checked ? 'block' : 'none';
    });
  }
});

async function submitTPSL(event) {
  event.preventDefault();
  
  const positionId = document.getElementById('tpslPositionId').value;
  const symbol = document.getElementById('tpslSymbol').value;
  const side = document.getElementById('tpslSide').value;
  
  const enableTP = document.getElementById('enableTP').checked;
  const enableSL = document.getElementById('enableSL').checked;
  const enableMaxHold = document.getElementById('enableMaxHold').checked;
  
  const tpslData = {
    accountId: state.currentAccountId,
    positionId,
    symbol,
    side
  };
  
  // 止盈设置
  if (enableTP) {
    const tpPrice = parseFloat(document.getElementById('takeProfitPrice').value);
    const tpRate = parseFloat(document.getElementById('takeProfitRate').value);
    
    if (!tpPrice && !tpRate) {
      showToast('请设置止盈价格或收益率', 'error');
      return;
    }
    
    tpslData.takeProfit = {
      price: tpPrice || null,
      rate: tpRate || null
    };
  }
  
  // 止损设置
  if (enableSL) {
    const slPrice = parseFloat(document.getElementById('stopLossPrice').value);
    const slRate = parseFloat(document.getElementById('stopLossRate').value);
    
    if (!slPrice && !slRate) {
      showToast('请设置止损价格或亏损率', 'error');
      return;
    }
    
    tpslData.stopLoss = {
      price: slPrice || null,
      rate: slRate || null
    };
  }
  
  // 最大持有周期
  if (enableMaxHold) {
    const timeframe = document.getElementById('maxHoldTimeframe').value;
    const bars = parseInt(document.getElementById('maxHoldBars').value);
    
    if (!bars || bars < 1) {
      showToast('请设置有效的K线数量', 'error');
      return;
    }
    
    tpslData.maxHold = {
      timeframe,
      bars
    };
  }
  
  if (!enableTP && !enableSL && !enableMaxHold) {
    showToast('请至少启用一项设置', 'error');
    return;
  }
  
  try {
    const response = await fetch('/api/debug2/position/set-tpsl', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(tpslData)
    });
    
    const data = await response.json();
    
    if (data.success) {
      showToast('止盈止损设置成功！', 'success');
      closeTPSLModal();
      loadPositions();
    } else {
      showToast(`设置失败: ${data.error}`, 'error');
    }
  } catch (error) {
    showToast(`设置失败: ${error.message}`, 'error');
  }
}

// 检查止盈止损状态
async function checkTPSLStatus(positionId) {
  if (!state.currentAccountId) return;
  
  try {
    const response = await fetch(`/api/live-trading-v2/position/${positionId}/tpsl-status?accountId=${state.currentAccountId}`);
    const data = await response.json();
    
    if (data.success && data.hasConfig) {
      let message = '📊 止盈止损状态\n\n';
      
      // 数据库配置
      message += '【本地配置】\n';
      if (data.config.takeProfitPrice) {
        message += `止盈价格: ${data.config.takeProfitPrice}\n`;
      }
      if (data.config.takeProfitRate) {
        message += `止盈收益率: ${data.config.takeProfitRate}%\n`;
      }
      if (data.config.stopLossPrice) {
        message += `止损价格: ${data.config.stopLossPrice}\n`;
      }
      if (data.config.stopLossRate) {
        message += `止损亏损率: ${data.config.stopLossRate}%\n`;
      }
      
      // OKX委托单状态
      message += '\n【OKX委托单】\n';
      if (data.okxOrders && data.okxOrders.length > 0) {
        data.okxOrders.forEach((order, idx) => {
          message += `委托单 ${idx + 1}:\n`;
          if (order.tpTriggerPrice) {
            message += `  止盈触发价: ${order.tpTriggerPrice}\n`;
          }
          if (order.slTriggerPrice) {
            message += `  止损触发价: ${order.slTriggerPrice}\n`;
          }
          message += `  状态: ${order.state}\n`;
        });
        message += '\n✅ 止盈止损已在OKX生效！';
      } else {
        message += '⚠️ 未找到OKX委托单\n';
        message += '请重新提交止盈止损设置';
      }
      
      // 最大持有周期进度
      if (data.holdingProgress) {
        const hp = data.holdingProgress;
        message += '\n\n【最大持有周期】\n';
        message += `周期: ${hp.timeframe}\n`;
        message += `最大K线: ${hp.maxBars}根\n`;
        message += `已持有: ${hp.elapsedBars}根\n`;
        message += `剩余: ${hp.remainingBars}根\n`;
        message += `进度: ${hp.progressPercent}%\n`;
        message += `开始时间: ${new Date(hp.createdAt).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}\n`;
        message += `将平仓于: ${new Date(hp.willCloseAt).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}`;
        
        if (hp.remainingBars === 0) {
          message += '\n\n⚠️ 已达到最大持有周期！';
        }
      }
      
      alert(message);
    } else {
      showToast('未设置止盈止损', 'info');
    }
  } catch (error) {
    console.error('检查状态失败:', error);
    showToast(`检查失败: ${error.message}`, 'error');
  }
}

// 防守加仓相关函数
let defenseTriggerType = 'down';  // 默认下跌加仓

function openDefenseAddModal(positionId, symbol, side, entryPrice, leverage) {
  document.getElementById('defensePositionId').value = positionId;
  document.getElementById('defenseSymbol').value = symbol;
  document.getElementById('defenseSide').value = side;
  document.getElementById('defenseAnchorPrice').value = entryPrice;
  document.getElementById('defenseLeverage').value = leverage;
  
  document.getElementById('displayAnchorPrice').textContent = entryPrice.toFixed(4);
  document.getElementById('displayLeverage').textContent = `${leverage}x`;
  
  // 重置表单
  document.getElementById('defenseAddForm').reset();
  document.getElementById('calculatedTriggerPrice').textContent = '触发价格: --';
  
  // 设置默认为下跌加仓
  setDefenseTriggerType('down');
  
  document.getElementById('defenseAddModal').classList.add('active');
}

function closeDefenseAddModal() {
  document.getElementById('defenseAddModal').classList.remove('active');
}

function setDefenseTriggerType(type) {
  defenseTriggerType = type;
  
  const downBtn = document.getElementById('triggerDown');
  const upBtn = document.getElementById('triggerUp');
  
  if (type === 'down') {
    downBtn.className = 'py-3 border-2 border-red-500 bg-red-50 text-red-600 rounded-lg font-semibold';
    upBtn.className = 'py-3 border-2 border-gray-300 text-gray-600 rounded-lg font-semibold hover:bg-gray-50';
  } else {
    downBtn.className = 'py-3 border-2 border-gray-300 text-gray-600 rounded-lg font-semibold hover:bg-gray-50';
    upBtn.className = 'py-3 border-2 border-green-500 bg-green-50 text-green-600 rounded-lg font-semibold';
  }
  
  // 重新计算触发价格
  calculateDefenseTriggerPrice();
}

// 计算触发价格
function calculateDefenseTriggerPrice() {
  const anchorPrice = parseFloat(document.getElementById('defenseAnchorPrice').value);
  const percentInput = document.getElementById('defenseTriggerPercent');
  const percent = parseFloat(percentInput.value);
  
  if (!percent || percent <= 0) {
    document.getElementById('calculatedTriggerPrice').textContent = '触发价格: --';
    return;
  }
  
  // 下跌用负数，上涨用正数
  const triggerPercent = defenseTriggerType === 'down' ? -percent : percent;
  const triggerPrice = anchorPrice * (1 + triggerPercent / 100);
  
  const direction = defenseTriggerType === 'down' ? '下跌' : '上涨';
  const color = defenseTriggerType === 'down' ? 'text-red-600' : 'text-green-600';
  
  document.getElementById('calculatedTriggerPrice').innerHTML = 
    `<span class="${color}">触发价格: ${triggerPrice.toFixed(4)} (${direction}${percent}%)</span>`;
}

// 监听百分比输入
document.addEventListener('DOMContentLoaded', function() {
  const percentInput = document.getElementById('defenseTriggerPercent');
  if (percentInput) {
    percentInput.addEventListener('input', calculateDefenseTriggerPrice);
  }
});

async function submitDefenseAdd(event) {
  event.preventDefault();
  
  const positionId = document.getElementById('defensePositionId').value;
  const symbol = document.getElementById('defenseSymbol').value;
  const side = document.getElementById('defenseSide').value;
  const anchorPrice = parseFloat(document.getElementById('defenseAnchorPrice').value);
  const leverage = parseInt(document.getElementById('defenseLeverage').value);
  const percent = parseFloat(document.getElementById('defenseTriggerPercent').value);
  const usdtAmount = parseFloat(document.getElementById('defenseUsdtAmount').value);
  
  if (!percent || percent <= 0) {
    showToast('请输入有效的触发百分比', 'error');
    return;
  }
  
  if (!usdtAmount || usdtAmount < 10) {
    showToast('加仓数量至少10 USDT', 'error');
    return;
  }
  
  // 计算触发百分比（下跌用负数，上涨用正数）
  const triggerPercent = defenseTriggerType === 'down' ? -percent : percent;
  const triggerPrice = anchorPrice * (1 + triggerPercent / 100);
  
  // 确认对话框
  const direction = defenseTriggerType === 'down' ? '下跌' : '上涨';
  const confirmMsg = `确认设置防守加仓？\n\n` +
    `交易对: ${symbol}\n` +
    `锚定价格: ${anchorPrice.toFixed(4)}\n` +
    `触发条件: ${direction} ${percent}%\n` +
    `触发价格: ${triggerPrice.toFixed(4)}\n` +
    `加仓数量: ${usdtAmount} USDT\n` +
    `杠杆倍数: ${leverage}x\n\n` +
    `⚠️ 此订单不占用余额，达到触发价格时自动执行`;
  
  if (!confirm(confirmMsg)) {
    return;
  }
  
  try {
    const response = await fetch('/api/debug2/position/defense-add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        accountId: state.currentAccountId,
        positionId,
        symbol,
        side,
        anchorPrice,
        triggerPercent,
        usdtAmount,
        leverage
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      showToast('防守加仓设置成功！', 'success');
      closeDefenseAddModal();
      
      // 显示详细信息
      setTimeout(() => {
        alert(`✅ 防守加仓已在OKX生效\n\n` +
          `触发价格: ${triggerPrice.toFixed(4)}\n` +
          `加仓数量: ${usdtAmount} USDT\n` +
          `杠杆倍数: ${leverage}x\n\n` +
          `当价格${direction}到触发价时，系统会自动加仓`);
      }, 500);
    } else {
      showToast(`设置失败: ${data.error}`, 'error');
    }
  } catch (error) {
    showToast(`设置失败: ${error.message}`, 'error');
  }
}

// 查看防守单列表
async function viewDefenseOrders(positionId, symbol) {
  if (!state.currentAccountId) return;
  
  try {
    const response = await fetch(`/api/live-trading-v2/position/${positionId}/defense-list?accountId=${state.currentAccountId}`);
    const data = await response.json();
    
    if (data.success) {
      if (data.orders.length === 0) {
        showToast('暂无防守单', 'info');
        return;
      }
      
      // 构建列表显示
      let message = `🛡️ ${symbol} 防守单列表\n\n`;
      
      data.orders.forEach((order, idx) => {
        message += `【防守单 ${idx + 1}】\n`;
        message += `方向: ${order.direction} ${Math.abs(order.triggerPercent)}%\n`;
        message += `锚定价格: ${order.anchorPrice}\n`;
        message += `触发价格: ${order.triggerPrice}\n`;
        message += `加仓数量: ${order.usdtAmount} USDT\n`;
        message += `杠杆倍数: ${order.leverage}x\n`;
        message += `OKX状态: ${order.okxStatus}\n`;
        message += `创建时间: ${new Date(order.createdAt).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}\n`;
        message += `\n[点击取消此防守单: ID ${order.id}]\n\n`;
      });
      
      message += '是否要取消某个防守单？\n';
      message += '请输入防守单ID，或点击取消返回';
      
      const input = prompt(message, '');
      
      if (input && input.trim()) {
        const defenseId = parseInt(input.trim());
        if (defenseId && data.orders.find(o => o.id === defenseId)) {
          await cancelDefenseOrder(defenseId);
        } else {
          showToast('无效的防守单ID', 'error');
        }
      }
    } else {
      showToast(`查询失败: ${data.error}`, 'error');
    }
  } catch (error) {
    console.error('查看防守单失败:', error);
    showToast(`查询失败: ${error.message}`, 'error');
  }
}

// 取消防守单
async function cancelDefenseOrder(defenseId) {
  if (!state.currentAccountId) return;
  
  if (!confirm(`确认取消防守单 #${defenseId}？\n\n此操作将同时取消OKX的委托单`)) {
    return;
  }
  
  try {
    const response = await fetch(`/api/live-trading-v2/defense/${defenseId}?accountId=${state.currentAccountId}`, {
      method: 'DELETE'
    });
    
    const data = await response.json();
    
    if (data.success) {
      showToast('防守单已取消', 'success');
      loadPositions(); // 刷新持仓列表
    } else {
      showToast(`取消失败: ${data.error}`, 'error');
    }
  } catch (error) {
    console.error('取消防守单失败:', error);
    showToast(`取消失败: ${error.message}`, 'error');
  }
}

// 一键清除所有防守单
async function clearAllDefenseOrders() {
  if (!state.currentAccountId) {
    showToast('请先选择账户', 'error');
    return;
  }
  
  if (!confirm('⚠️ 确认要清除所有防守单吗？\n\n此操作将：\n1. 取消所有持仓的所有防守单\n2. 同时取消OKX上的对应委托单\n3. 此操作不可撤销！\n\n确认继续？')) {
    return;
  }
  
  try {
    showToast('正在清除所有防守单...', 'info');
    
    const response = await fetch(`/api/live-trading-v2/defense/clear-all?accountId=${state.currentAccountId}`, {
      method: 'DELETE'
    });
    
    const data = await response.json();
    
    if (data.success) {
      const count = data.canceledCount || 0;
      showToast(`✅ 成功清除 ${count} 个防守单`, 'success');
      loadPositions(); // 刷新持仓列表
    } else {
      showToast(`清除失败: ${data.error}`, 'error');
    }
  } catch (error) {
    console.error('清除所有防守单失败:', error);
    showToast(`清除失败: ${error.message}`, 'error');
  }
}

// 取消所有未成交的委托单
async function cancelAllPendingOrders() {
  if (!state.currentAccountId) {
    showToast('请先选择账户', 'error');
    return;
  }
  
  if (!confirm('⚠️ 确认要取消所有未成交的委托单吗？\n\n此操作将：\n1. 取消所有挂单状态的委托单\n2. 同时取消OKX上的对应委托\n3. 不会影响已成交的订单\n4. 此操作不可撤销！\n\n确认继续？')) {
    return;
  }
  
  try {
    showToast('正在取消所有未成交委托单...', 'info');
    
    const response = await fetch(`/api/live-trading-v2/orders/cancel-all-pending?accountId=${state.currentAccountId}`, {
      method: 'DELETE'
    });
    
    const data = await response.json();
    
    if (data.success) {
      const count = data.canceledCount || 0;
      showToast(`✅ 成功取消 ${count} 个未成交委托单`, 'success');
      loadPositions(); // 刷新持仓列表
    } else {
      showToast(`取消失败: ${data.error}`, 'error');
    }
  } catch (error) {
    console.error('取消所有未成交委托单失败:', error);
    showToast(`取消失败: ${error.message}`, 'error');
  }
}

// ============ 历史订单 ============

// 打开历史订单
function openTradeHistory() {
  if (!state.currentAccountId) {
    showToast('请先选择账户', 'error');
    return;
  }
  
  document.getElementById('tradeHistoryModal').classList.add('active');
  
  // 填充币种筛选器
  const symbolFilter = document.getElementById('historySymbolFilter');
  symbolFilter.innerHTML = '<option value="">所有币种</option>';
  SYMBOLS.forEach(symbol => {
    symbolFilter.innerHTML += `<option value="${symbol}">${symbol}/USDT</option>`;
  });
  
  loadTradeHistory();
}

// 关闭历史订单
function closeTradeHistory() {
  document.getElementById('tradeHistoryModal').classList.remove('active');
}

// 加载历史订单
async function loadTradeHistory() {
  if (!state.currentAccountId) return;
  
  try {
    const symbol = document.getElementById('historySymbolFilter')?.value || '';
    const tradeType = document.getElementById('historyTypeFilter')?.value || '';
    const days = document.getElementById('historyDaysFilter')?.value || '30';
    
    const params = new URLSearchParams({
      accountId: state.currentAccountId,
      days,
      limit: '100'
    });
    
    if (symbol) params.append('symbol', symbol);
    if (tradeType) params.append('tradeType', tradeType);
    
    const response = await fetch(`/api/live-trading-v2/trade-history?${params}`);
    const data = await response.json();
    
    const container = document.getElementById('tradeHistoryList');
    
    if (data.success && data.data && data.data.length > 0) {
      container.innerHTML = `
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-gray-100 sticky top-0">
              <tr>
                <th class="px-3 py-2 text-left">时间</th>
                <th class="px-3 py-2 text-left">币种</th>
                <th class="px-3 py-2 text-left">类型</th>
                <th class="px-3 py-2 text-right">价格</th>
                <th class="px-3 py-2 text-right">数量</th>
                <th class="px-3 py-2 text-right">金额</th>
                <th class="px-3 py-2 text-center">杠杆</th>
                <th class="px-3 py-2 text-right">盈亏</th>
                <th class="px-3 py-2 text-right">手续费</th>
                <th class="px-3 py-2 text-center">状态</th>
              </tr>
            </thead>
            <tbody>
              ${data.data.map(trade => {
                const tradeTypeMap = {
                  'open_long': '🟢 开多',
                  'open_short': '🔴 开空',
                  'close_long': '🟢 平多',
                  'close_short': '🔴 平空',
                  'add_position': '➕ 加仓'
                };
                
                const pnlColor = trade.pnl > 0 ? 'text-green-600' : trade.pnl < 0 ? 'text-red-600' : 'text-gray-600';
                const statusColor = trade.status === 'completed' ? 'text-green-600' : trade.status === 'failed' ? 'text-red-600' : 'text-yellow-600';
                const statusText = trade.status === 'completed' ? '✅ 已完成' : trade.status === 'failed' ? '❌ 失败' : '⏳ 进行中';
                
                const time = new Date(trade.trade_time).toLocaleString('zh-CN', {
                  timeZone: 'Asia/Shanghai',
                  month: '2-digit',
                  day: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit'
                });
                
                return `
                  <tr class="border-b hover:bg-gray-50">
                    <td class="px-3 py-2 text-gray-600">${time}</td>
                    <td class="px-3 py-2 font-semibold">${trade.symbol}</td>
                    <td class="px-3 py-2">${tradeTypeMap[trade.trade_type] || trade.trade_type}</td>
                    <td class="px-3 py-2 text-right">${parseFloat(trade.price).toFixed(4)}</td>
                    <td class="px-3 py-2 text-right">${trade.size}</td>
                    <td class="px-3 py-2 text-right font-semibold">${parseFloat(trade.usdt_amount).toFixed(2)} USDT</td>
                    <td class="px-3 py-2 text-center">${trade.leverage}x</td>
                    <td class="px-3 py-2 text-right font-semibold ${pnlColor}">
                      ${trade.pnl ? (trade.pnl > 0 ? '+' : '') + parseFloat(trade.pnl).toFixed(2) + ' USDT' : '-'}
                      ${trade.pnl_rate ? `<br><span class="text-xs">(${(trade.pnl_rate > 0 ? '+' : '')}${trade.pnl_rate.toFixed(2)}%)</span>` : ''}
                    </td>
                    <td class="px-3 py-2 text-right text-red-600">${trade.fee ? parseFloat(trade.fee).toFixed(4) : '-'}</td>
                    <td class="px-3 py-2 text-center ${statusColor}">${statusText}</td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
        <div class="mt-4 text-sm text-gray-600 text-center">
          共 ${data.total} 条记录
        </div>
      `;
    } else {
      container.innerHTML = `
        <div class="text-center text-gray-500 py-8">
          <i class="fas fa-inbox text-3xl mb-2"></i>
          <div class="text-sm">暂无历史记录</div>
        </div>
      `;
    }
  } catch (error) {
    console.error('加载历史订单失败:', error);
    showToast(`加载失败: ${error.message}`, 'error');
  }
}

// 导出历史订单为CSV
async function exportTradeHistoryCSV() {
  if (!state.currentAccountId) return;
  
  try {
    const symbol = document.getElementById('historySymbolFilter')?.value || '';
    const tradeType = document.getElementById('historyTypeFilter')?.value || '';
    const days = document.getElementById('historyDaysFilter')?.value || '30';
    
    const params = new URLSearchParams({
      accountId: state.currentAccountId,
      days
    });
    
    if (symbol) params.append('symbol', symbol);
    if (tradeType) params.append('tradeType', tradeType);
    
    const response = await fetch(`/api/live-trading-v2/trade-history/export?${params}`);
    
    if (response.ok) {
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `trade_history_${state.currentAccountId}_${Date.now()}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      showToast('导出成功！', 'success');
    } else {
      showToast('导出失败', 'error');
    }
  } catch (error) {
    console.error('导出CSV失败:', error);
    showToast(`导出失败: ${error.message}`, 'error');
  }
}

// 实盘交易控制中心 - 前端逻辑

// 全局状态
const state = {
    accounts: [], // 所有账户列表
    currentAccountId: null, // 当前选中的账户ID
    tradingConfig: {
        mode: 'auto', // auto / semi-auto
        strategy: '',
        symbol: '',
        direction: 'long', // long / short
        leverage: 10,
        positionRatio: 30, // 百分比
        fundsPartition: 10, // 分份数
        fundsUpperLimit: 10000,
        fundsLowerLimit: 100
    }
};

// DOM 加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('📊 实盘交易页面加载完成');
    
    // 初始化事件监听器
    initEventListeners();
    
    // 加载账户列表
    loadAccounts();
    
    // 加载币种列表
    loadSymbols();
    
    // 初始化滑块
    initSliders();
});

// 初始化事件监听器
function initEventListeners() {
    // 刷新所有账户按钮
    document.getElementById('refreshAllBtn').addEventListener('click', refreshAllAccounts);
    
    // 添加账户按钮
    document.getElementById('addAccountBtn').addEventListener('click', showAddAccountModal);
    
    // 模态框按钮
    document.getElementById('cancelAddAccountBtn').addEventListener('click', hideAddAccountModal);
    document.getElementById('confirmAddAccountBtn').addEventListener('click', confirmAddAccount);
    
    // 交易模式切换
    document.querySelectorAll('[data-mode]').forEach(btn => {
        btn.addEventListener('click', function() {
            const mode = this.getAttribute('data-mode');
            switchTradingMode(mode);
        });
    });
    
    // 交易方向切换
    document.querySelectorAll('[data-direction]').forEach(btn => {
        btn.addEventListener('click', function() {
            const direction = this.getAttribute('data-direction');
            switchDirection(direction);
        });
    });
    
    // 策略选择
    document.getElementById('strategySelect').addEventListener('change', function() {
        state.tradingConfig.strategy = this.value;
        console.log('策略切换:', this.value);
    });
    
    // 币种选择
    document.getElementById('symbolSelect').addEventListener('change', function() {
        state.tradingConfig.symbol = this.value;
        console.log('币种切换:', this.value);
    });
    
    // 资金分份输入
    document.getElementById('fundsPartition').addEventListener('input', function() {
        state.tradingConfig.fundsPartition = parseInt(this.value) || 1;
        updatePerPartAmount();
    });
    
    // 托管资金限制输入
    document.getElementById('fundsUpperLimit').addEventListener('input', function() {
        state.tradingConfig.fundsUpperLimit = parseFloat(this.value) || 0;
        updatePerPartAmount();
    });
    
    document.getElementById('fundsLowerLimit').addEventListener('input', function() {
        state.tradingConfig.fundsLowerLimit = parseFloat(this.value) || 0;
    });
    
    // 操作按钮
    document.getElementById('saveConfigBtn').addEventListener('click', saveConfig);
    document.getElementById('startTradingBtn').addEventListener('click', startTrading);
    document.getElementById('stopTradingBtn').addEventListener('click', stopTrading);
    
    // 做多做空操作按钮
    document.getElementById('openLongBtn').addEventListener('click', () => openPosition('long'));
    document.getElementById('closeLongBtn').addEventListener('click', () => closePosition('long'));
    document.getElementById('openShortBtn').addEventListener('click', () => openPosition('short'));
    document.getElementById('closeShortBtn').addEventListener('click', () => closePosition('short'));
    document.getElementById('closeAllBtn').addEventListener('click', closeAllPositions);
}

// 初始化滑块
function initSliders() {
    // 杠杆倍数滑块
    const leverageSlider = document.getElementById('leverageSlider');
    const leverageValue = document.getElementById('leverageValue');
    
    leverageSlider.addEventListener('input', function() {
        const value = parseInt(this.value);
        state.tradingConfig.leverage = value;
        leverageValue.textContent = value + 'x';
    });
    
    // 持仓占比滑块
    const positionRatioSlider = document.getElementById('positionRatioSlider');
    const positionRatioValue = document.getElementById('positionRatioValue');
    
    positionRatioSlider.addEventListener('input', function() {
        const value = parseInt(this.value);
        state.tradingConfig.positionRatio = value;
        positionRatioValue.textContent = value + '%';
        updatePerPartAmount();
    });
}

// 加载账户列表
async function loadAccounts() {
    try {
        console.log('📥 加载账户列表...');
        const response = await fetch('/api/live-trading/accounts');
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            state.accounts = data.accounts || [];
            console.log(`✅ 加载了 ${state.accounts.length} 个账户`);
            renderAccounts();
        } else {
            throw new Error(data.error || '加载账户失败');
        }
    } catch (error) {
        console.error('❌ 加载账户失败:', error);
        showNotification('加载账户失败: ' + error.message, 'error');
    }
}

// 渲染账户列表
function renderAccounts() {
    const accountsGrid = document.getElementById('accountsGrid');
    
    if (state.accounts.length === 0) {
        accountsGrid.innerHTML = `
            <div class="text-center py-12 text-gray-400 col-span-full">
                <i class="fas fa-wallet text-6xl mb-4"></i>
                <p>暂无账户，请点击"添加账户"开始</p>
            </div>
        `;
        return;
    }
    
    accountsGrid.innerHTML = state.accounts.map(account => `
        <div class="account-card bg-white rounded-lg p-6 shadow-md cursor-pointer ${account.id === state.currentAccountId ? 'active' : ''}"
             data-account-id="${account.id}">
            <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-bold text-gray-800">${escapeHtml(account.name)}</h3>
                <div class="flex items-center gap-2">
                    <span class="px-2 py-1 text-xs rounded-full ${account.is_testnet ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'}">
                        ${account.is_testnet ? '测试网' : '正式网'}
                    </span>
                    <button class="text-red-500 hover:text-red-700" onclick="deleteAccount('${account.id}', event)">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            
            <div class="space-y-2 text-sm">
                <div class="flex justify-between">
                    <span class="text-gray-600">交易余额:</span>
                    <span class="font-bold">${account.trading_balance ? account.trading_balance.toFixed(2) : '--'} USDT</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-600">资金余额:</span>
                    <span class="font-bold">${account.funding_balance ? account.funding_balance.toFixed(2) : '--'} USDT</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-600">当日盈亏:</span>
                    <span class="${account.daily_pnl >= 0 ? 'profit-positive' : 'profit-negative'}">
                        ${account.daily_pnl ? (account.daily_pnl >= 0 ? '+' : '') + account.daily_pnl.toFixed(2) : '--'} USDT
                    </span>
                </div>
            </div>
            
            <div class="mt-4 pt-4 border-t border-gray-200 flex justify-between items-center">
                <span class="text-xs text-gray-500">
                    <i class="fas fa-clock mr-1"></i>
                    ${account.last_update ? new Date(account.last_update).toLocaleString('zh-CN') : '未更新'}
                </span>
                <button class="text-blue-600 hover:text-blue-800 text-sm" onclick="refreshAccount('${account.id}', event)">
                    <i class="fas fa-sync-alt mr-1"></i>刷新
                </button>
            </div>
        </div>
    `).join('');
    
    // 添加点击事件
    document.querySelectorAll('.account-card').forEach(card => {
        card.addEventListener('click', function(e) {
            // 如果点击的是按钮，不触发选择
            if (e.target.closest('button')) return;
            
            const accountId = this.getAttribute('data-account-id');
            selectAccount(accountId);
        });
    });
}

// 选择账户
function selectAccount(accountId) {
    state.currentAccountId = accountId;
    const account = state.accounts.find(a => a.id === accountId);
    
    if (!account) {
        console.error('账户不存在:', accountId);
        return;
    }
    
    console.log('✅ 选中账户:', account.name);
    
    // 更新UI
    renderAccounts();
    showAccountDetails(account);
    
    // 加载该账户的持仓和历史
    loadPositions(accountId);
    loadHistory(accountId);
}

// 显示账户详情
function showAccountDetails(account) {
    const detailsSection = document.getElementById('selectedAccountDetails');
    detailsSection.classList.remove('hidden');
    
    // 更新账户名称
    document.getElementById('currentAccountName').textContent = account.name;
    
    // 更新余额统计
    document.getElementById('tradingBalance').textContent = account.trading_balance ? account.trading_balance.toFixed(2) : '0.00';
    document.getElementById('fundingBalance').textContent = account.funding_balance ? account.funding_balance.toFixed(2) : '0.00';
    
    const dailyPnL = account.daily_pnl || 0;
    const dailyPnLElement = document.getElementById('dailyPnL');
    dailyPnLElement.textContent = (dailyPnL >= 0 ? '+' : '') + dailyPnL.toFixed(2);
    dailyPnLElement.className = dailyPnL >= 0 ? 'text-3xl font-bold profit-positive' : 'text-3xl font-bold profit-negative';
    
    const totalBalance = (account.trading_balance || 0) + (account.funding_balance || 0);
    const dailyPnLPercent = totalBalance > 0 ? (dailyPnL / totalBalance * 100).toFixed(2) : '0.00';
    document.getElementById('dailyPnLPercent').textContent = dailyPnLPercent + '%';
    
    // 更新每份金额
    updatePerPartAmount();
}

// 更新每份金额显示
function updatePerPartAmount() {
    if (!state.currentAccountId) return;
    
    const account = state.accounts.find(a => a.id === state.currentAccountId);
    if (!account) return;
    
    const tradingBalance = account.trading_balance || 0;
    const upperLimit = state.tradingConfig.fundsUpperLimit;
    const positionRatio = state.tradingConfig.positionRatio / 100;
    const partition = state.tradingConfig.fundsPartition;
    
    // 可用资金 = min(交易余额, 上限) * 持仓占比
    const availableFunds = Math.min(tradingBalance, upperLimit) * positionRatio;
    const perPartAmount = availableFunds / partition;
    
    document.getElementById('perPartAmount').value = perPartAmount.toFixed(2);
}

// 刷新所有账户
async function refreshAllAccounts() {
    console.log('🔄 刷新所有账户...');
    showNotification('正在刷新所有账户...', 'info');
    
    for (const account of state.accounts) {
        await refreshAccount(account.id);
        // 每个账户之间等待0.5秒，避免API限流
        await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    showNotification('所有账户刷新完成', 'success');
}

// 刷新单个账户
async function refreshAccount(accountId, event) {
    if (event) {
        event.stopPropagation(); // 阻止事件冒泡
    }
    
    try {
        console.log('🔄 刷新账户:', accountId);
        const response = await fetch(`/api/live-trading/accounts/${accountId}/refresh`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            console.log('✅ 账户刷新成功');
            // 更新本地状态
            const accountIndex = state.accounts.findIndex(a => a.id === accountId);
            if (accountIndex !== -1) {
                state.accounts[accountIndex] = { ...state.accounts[accountIndex], ...data.account };
            }
            renderAccounts();
            
            // 如果是当前选中的账户，更新详情
            if (state.currentAccountId === accountId) {
                showAccountDetails(data.account);
            }
        } else {
            throw new Error(data.error || '刷新失败');
        }
    } catch (error) {
        console.error('❌ 刷新账户失败:', error);
        showNotification('刷新账户失败: ' + error.message, 'error');
    }
}

// 显示添加账户模态框
function showAddAccountModal() {
    document.getElementById('addAccountModal').classList.remove('hidden');
}

// 隐藏添加账户模态框
function hideAddAccountModal() {
    document.getElementById('addAccountModal').classList.add('hidden');
    // 清空输入
    document.getElementById('accountNameInput').value = '';
    document.getElementById('apiKeyInput').value = '';
    document.getElementById('secretKeyInput').value = '';
    document.getElementById('passphraseInput').value = '';
    document.getElementById('testnetCheckbox').checked = false;
}

// 确认添加账户
async function confirmAddAccount() {
    const name = document.getElementById('accountNameInput').value.trim();
    const apiKey = document.getElementById('apiKeyInput').value.trim();
    const secretKey = document.getElementById('secretKeyInput').value.trim();
    const passphrase = document.getElementById('passphraseInput').value.trim();
    const isTestnet = document.getElementById('testnetCheckbox').checked;
    
    if (!name || !apiKey || !secretKey || !passphrase) {
        showNotification('请填写所有必填字段', 'error');
        return;
    }
    
    try {
        console.log('➕ 添加账户:', name);
        const response = await fetch('/api/live-trading/accounts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name,
                api_key: apiKey,
                secret_key: secretKey,
                passphrase,
                is_testnet: isTestnet
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            console.log('✅ 账户添加成功');
            showNotification('账户添加成功', 'success');
            hideAddAccountModal();
            loadAccounts(); // 重新加载账户列表
        } else {
            throw new Error(data.error || '添加失败');
        }
    } catch (error) {
        console.error('❌ 添加账户失败:', error);
        showNotification('添加账户失败: ' + error.message, 'error');
    }
}

// 删除账户
async function deleteAccount(accountId, event) {
    if (event) {
        event.stopPropagation();
    }
    
    if (!confirm('确定要删除此账户吗？此操作不可恢复！')) {
        return;
    }
    
    try {
        console.log('🗑️ 删除账户:', accountId);
        const response = await fetch(`/api/live-trading/accounts/${accountId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            console.log('✅ 账户删除成功');
            showNotification('账户删除成功', 'success');
            
            // 如果删除的是当前选中的账户，清空选择
            if (state.currentAccountId === accountId) {
                state.currentAccountId = null;
                document.getElementById('selectedAccountDetails').classList.add('hidden');
            }
            
            loadAccounts(); // 重新加载账户列表
        } else {
            throw new Error(data.error || '删除失败');
        }
    } catch (error) {
        console.error('❌ 删除账户失败:', error);
        showNotification('删除账户失败: ' + error.message, 'error');
    }
}

// 加载币种列表
async function loadSymbols() {
    try {
        console.log('📥 加载币种列表...');
        const response = await fetch('/api/kline/symbols');
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success && data.symbols) {
            const symbolSelect = document.getElementById('symbolSelect');
            symbolSelect.innerHTML = '<option value="">-- 请选择币种 --</option>' +
                data.symbols.map(symbol => `<option value="${symbol}">${symbol}</option>`).join('');
            console.log(`✅ 加载了 ${data.symbols.length} 个币种`);
        } else {
            throw new Error(data.error || '加载币种失败');
        }
    } catch (error) {
        console.error('❌ 加载币种失败:', error);
        document.getElementById('symbolSelect').innerHTML = '<option value="">加载失败</option>';
    }
}

// 切换交易模式
function switchTradingMode(mode) {
    state.tradingConfig.mode = mode;
    
    // 更新按钮样式
    document.querySelectorAll('[data-mode]').forEach(btn => {
        if (btn.getAttribute('data-mode') === mode) {
            btn.classList.add('active', 'bg-green-600', 'text-white');
            btn.classList.remove('bg-white', 'text-gray-700');
        } else {
            btn.classList.remove('active', 'bg-green-600', 'text-white');
            btn.classList.add('bg-white', 'text-gray-700');
        }
    });
    
    console.log('交易模式切换:', mode);
}

// 切换交易方向
function switchDirection(direction) {
    state.tradingConfig.direction = direction;
    
    // 更新按钮样式
    document.querySelectorAll('[data-direction]').forEach(btn => {
        if (btn.getAttribute('data-direction') === direction) {
            if (direction === 'long') {
                btn.classList.add('active', 'bg-green-600', 'text-white', 'border-green-600');
                btn.classList.remove('bg-white', 'text-gray-700', 'bg-green-50', 'text-green-700', 'border-green-500');
            } else {
                btn.classList.add('active', 'bg-red-600', 'text-white', 'border-red-600');
                btn.classList.remove('bg-white', 'text-gray-700');
            }
        } else {
            btn.classList.remove('active', 'bg-green-600', 'bg-red-600', 'text-white', 'border-green-600', 'border-red-600');
            if (direction === 'short' && btn.getAttribute('data-direction') === 'long') {
                btn.classList.add('bg-green-50', 'text-green-700', 'border-green-500');
            } else {
                btn.classList.add('bg-white', 'text-gray-700');
            }
        }
    });
    
    console.log('交易方向切换:', direction);
}

// 加载持仓
async function loadPositions(accountId) {
    try {
        console.log('📥 加载持仓...');
        const response = await fetch(`/api/live-trading/accounts/${accountId}/positions`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            renderPositions(data.positions || []);
        } else {
            throw new Error(data.error || '加载持仓失败');
        }
    } catch (error) {
        console.error('❌ 加载持仓失败:', error);
        document.getElementById('positionsTableBody').innerHTML = `
            <tr>
                <td colspan="8" class="px-4 py-4 text-center text-red-500">
                    加载失败: ${escapeHtml(error.message)}
                </td>
            </tr>
        `;
    }
}

// 渲染持仓表格
function renderPositions(positions) {
    const tbody = document.getElementById('positionsTableBody');
    
    if (positions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="px-4 py-8 text-center text-gray-400">
                    <i class="fas fa-inbox text-4xl mb-2"></i>
                    <p>暂无持仓</p>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = positions.map(pos => {
        const pnl = pos.unrealized_pnl || 0;
        const pnlPercent = pos.unrealized_pnl_percent || 0;
        
        return `
            <tr class="hover:bg-gray-50">
                <td class="px-4 py-3 font-medium">${escapeHtml(pos.symbol)}</td>
                <td class="px-4 py-3">
                    <span class="px-2 py-1 text-xs rounded-full ${pos.side === 'long' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
                        ${pos.side === 'long' ? '做多' : '做空'}
                    </span>
                </td>
                <td class="px-4 py-3 text-right">${pos.quantity || 0}</td>
                <td class="px-4 py-3 text-right">$${(pos.entry_price || 0).toFixed(2)}</td>
                <td class="px-4 py-3 text-right">$${(pos.current_price || 0).toFixed(2)}</td>
                <td class="px-4 py-3 text-right ${pnl >= 0 ? 'profit-positive' : 'profit-negative'}">
                    ${pnl >= 0 ? '+' : ''}${pnl.toFixed(2)} USDT
                </td>
                <td class="px-4 py-3 text-right ${pnlPercent >= 0 ? 'profit-positive' : 'profit-negative'}">
                    ${pnlPercent >= 0 ? '+' : ''}${pnlPercent.toFixed(2)}%
                </td>
                <td class="px-4 py-3 text-center">
                    <button class="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm" onclick="closePosition('${pos.id}')">
                        平仓
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

// 加载交易历史
async function loadHistory(accountId) {
    try {
        console.log('📥 加载交易历史...');
        const response = await fetch(`/api/live-trading/accounts/${accountId}/history?limit=50`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            renderHistory(data.history || []);
        } else {
            throw new Error(data.error || '加载历史失败');
        }
    } catch (error) {
        console.error('❌ 加载历史失败:', error);
        document.getElementById('historyTableBody').innerHTML = `
            <tr>
                <td colspan="8" class="px-4 py-4 text-center text-red-500">
                    加载失败: ${escapeHtml(error.message)}
                </td>
            </tr>
        `;
    }
}

// 渲染交易历史表格
function renderHistory(history) {
    const tbody = document.getElementById('historyTableBody');
    
    if (history.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="px-4 py-8 text-center text-gray-400">
                    <i class="fas fa-inbox text-4xl mb-2"></i>
                    <p>暂无交易历史</p>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = history.map(trade => `
        <tr class="hover:bg-gray-50">
            <td class="px-4 py-3 text-sm">${new Date(trade.timestamp).toLocaleString('zh-CN')}</td>
            <td class="px-4 py-3 font-medium">${escapeHtml(trade.symbol)}</td>
            <td class="px-4 py-3">
                <span class="px-2 py-1 text-xs rounded-full ${trade.side === 'buy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
                    ${trade.side === 'buy' ? '买入' : '卖出'}
                </span>
            </td>
            <td class="px-4 py-3">${escapeHtml(trade.type)}</td>
            <td class="px-4 py-3 text-right">$${(trade.price || 0).toFixed(2)}</td>
            <td class="px-4 py-3 text-right">${trade.quantity || 0}</td>
            <td class="px-4 py-3 text-right">${(trade.amount || 0).toFixed(2)} USDT</td>
            <td class="px-4 py-3">
                <span class="px-2 py-1 text-xs rounded-full ${trade.status === 'filled' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}">
                    ${trade.status}
                </span>
            </td>
        </tr>
    `).join('');
}

// 保存配置
async function saveConfig() {
    if (!state.currentAccountId) {
        showNotification('请先选择一个账户', 'error');
        return;
    }
    
    try {
        console.log('💾 保存配置...');
        const response = await fetch(`/api/live-trading/accounts/${state.currentAccountId}/config`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(state.tradingConfig)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            console.log('✅ 配置保存成功');
            showNotification('配置保存成功', 'success');
        } else {
            throw new Error(data.error || '保存失败');
        }
    } catch (error) {
        console.error('❌ 保存配置失败:', error);
        showNotification('保存配置失败: ' + error.message, 'error');
    }
}

// 启动交易
async function startTrading() {
    if (!state.currentAccountId) {
        showNotification('请先选择一个账户', 'error');
        return;
    }
    
    if (!state.tradingConfig.strategy || !state.tradingConfig.symbol) {
        showNotification('请先选择策略和币种', 'error');
        return;
    }
    
    if (!confirm('确定要启动自动交易吗？')) {
        return;
    }
    
    try {
        console.log('▶️ 启动交易...');
        const response = await fetch(`/api/live-trading/accounts/${state.currentAccountId}/start`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(state.tradingConfig)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            console.log('✅ 交易启动成功');
            showNotification('交易已启动', 'success');
        } else {
            throw new Error(data.error || '启动失败');
        }
    } catch (error) {
        console.error('❌ 启动交易失败:', error);
        showNotification('启动交易失败: ' + error.message, 'error');
    }
}

// 停止交易
async function stopTrading() {
    if (!state.currentAccountId) {
        showNotification('请先选择一个账户', 'error');
        return;
    }
    
    if (!confirm('确定要停止交易吗？')) {
        return;
    }
    
    try {
        console.log('⏹️ 停止交易...');
        const response = await fetch(`/api/live-trading/accounts/${state.currentAccountId}/stop`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            console.log('✅ 交易停止成功');
            showNotification('交易已停止', 'success');
        } else {
            throw new Error(data.error || '停止失败');
        }
    } catch (error) {
        console.error('❌ 停止交易失败:', error);
        showNotification('停止交易失败: ' + error.message, 'error');
    }
}

// 平仓
async function closePosition(positionId) {
    if (!confirm('确定要平仓吗？')) {
        return;
    }
    
    try {
        console.log('📤 平仓...');
        const response = await fetch(`/api/live-trading/positions/${positionId}/close`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            console.log('✅ 平仓成功');
            showNotification('平仓成功', 'success');
            // 重新加载持仓
            if (state.currentAccountId) {
                loadPositions(state.currentAccountId);
                loadHistory(state.currentAccountId);
                refreshAccount(state.currentAccountId);
            }
        } else {
            throw new Error(data.error || '平仓失败');
        }
    } catch (error) {
        console.error('❌ 平仓失败:', error);
        showNotification('平仓失败: ' + error.message, 'error');
    }
}

// 显示通知
function showNotification(message, type = 'info') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 ${
        type === 'success' ? 'bg-green-600' :
        type === 'error' ? 'bg-red-600' :
        type === 'warning' ? 'bg-yellow-600' :
        'bg-blue-600'
    }`;
    
    const icon = 
        type === 'success' ? 'fa-check-circle' :
        type === 'error' ? 'fa-exclamation-circle' :
        type === 'warning' ? 'fa-exclamation-triangle' :
        'fa-info-circle';
    
    notification.innerHTML = `
        <div class="flex items-center gap-2">
            <i class="fas ${icon}"></i>
            <span>${escapeHtml(message)}</span>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // 3秒后自动移除
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        notification.style.transition = 'all 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// HTML 转义
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

// ========================================
// 交易操作函数
// ========================================

// 开仓操作
async function openPosition(direction) {
    if (!state.currentAccountId) {
        showNotification('请先选择一个账户', 'warning');
        return;
    }
    
    const symbol = state.tradingConfig.symbol;
    if (!symbol) {
        showNotification('请先选择交易币种', 'warning');
        return;
    }
    
    const directionText = direction === 'long' ? '做多' : '做空';
    
    // 确认对话框
    if (state.tradingConfig.mode === 'semi-auto') {
        const confirmed = confirm(
            `确认开仓操作？\n\n` +
            `方向: ${directionText}\n` +
            `币种: ${symbol}\n` +
            `杠杆: ${state.tradingConfig.leverage}x\n` +
            `持仓占比: ${state.tradingConfig.positionRatio}%\n\n` +
            `此操作将消耗资金并开立${directionText}仓位。`
        );
        if (!confirmed) return;
    }
    
    try {
        showNotification(`正在开${directionText}仓: ${symbol}...`, 'info');
        
        // 调用开仓API
        const response = await fetch(`/api/live-trading/positions/open`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                accountId: state.currentAccountId,
                symbol: symbol,
                direction: direction,
                leverage: state.tradingConfig.leverage,
                amount: calculatePositionAmount()
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || '开仓失败');
        }
        
        const result = await response.json();
        showNotification(`${directionText}仓位开仓成功！`, 'success');
        
        // 刷新持仓和账户信息
        await loadPositions(state.currentAccountId);
        await refreshAccount(state.currentAccountId);
        
    } catch (error) {
        console.error('开仓失败:', error);
        showNotification(`开${directionText}仓失败: ${error.message}`, 'error');
    }
}

// 平仓操作 (按方向)
async function closePosition(direction) {
    if (!state.currentAccountId) {
        showNotification('请先选择一个账户', 'warning');
        return;
    }
    
    const directionText = direction === 'long' ? '多' : '空';
    
    // 确认对话框
    const confirmed = confirm(
        `确认平仓操作？\n\n` +
        `将平掉所有${directionText}仓持仓\n\n` +
        `此操作不可撤销！`
    );
    if (!confirmed) return;
    
    try {
        showNotification(`正在平${directionText}仓...`, 'info');
        
        // 调用平仓API
        const response = await fetch(`/api/live-trading/positions/close-by-direction`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                accountId: state.currentAccountId,
                direction: direction
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || '平仓失败');
        }
        
        const result = await response.json();
        showNotification(`所有${directionText}仓已平仓！`, 'success');
        
        // 刷新持仓和账户信息
        await loadPositions(state.currentAccountId);
        await refreshAccount(state.currentAccountId);
        
    } catch (error) {
        console.error('平仓失败:', error);
        showNotification(`平${directionText}仓失败: ${error.message}`, 'error');
    }
}

// 全部平仓
async function closeAllPositions() {
    if (!state.currentAccountId) {
        showNotification('请先选择一个账户', 'warning');
        return;
    }
    
    // 确认对话框
    const confirmed = confirm(
        `⚠️ 危险操作！\n\n` +
        `确认平掉所有持仓吗？\n` +
        `包括所有做多和做空的仓位\n\n` +
        `此操作不可撤销！`
    );
    if (!confirmed) return;
    
    try {
        showNotification('正在平掉所有仓位...', 'info');
        
        // 调用全部平仓API
        const response = await fetch(`/api/live-trading/positions/close-all`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                accountId: state.currentAccountId
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || '全部平仓失败');
        }
        
        const result = await response.json();
        showNotification('所有仓位已平仓！', 'success');
        
        // 刷新持仓和账户信息
        await loadPositions(state.currentAccountId);
        await refreshAccount(state.currentAccountId);
        
    } catch (error) {
        console.error('全部平仓失败:', error);
        showNotification('全部平仓失败: ' + error.message, 'error');
    }
}

// 计算仓位金额
function calculatePositionAmount() {
    const upperLimit = state.tradingConfig.fundsUpperLimit;
    const positionRatio = state.tradingConfig.positionRatio / 100;
    const partition = state.tradingConfig.fundsPartition;
    
    // 计算可用资金
    const availableFunds = upperLimit * positionRatio;
    
    // 每份金额
    const perPartAmount = availableFunds / partition;
    
    return perPartAmount;
}

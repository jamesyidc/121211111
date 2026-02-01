/**
 * Filtered Signals API - 纯 JS 模块
 * 可以独立使用或集成到其他项目
 * @version 1.0.0
 */

class FilteredSignalsAPI {
    constructor(config = {}) {
        this.config = {
            apiBaseUrl: config.apiBaseUrl || '',
            defaultLimit: config.defaultLimit || 100,
            autoRefresh: config.autoRefresh !== false,
            refreshInterval: config.refreshInterval || 10000, // 10秒
            debug: config.debug || false
        };
        
        this.data = {
            allData: [],
            filteredData: [],
            homepageStats: null,
            lastLoadTime: null
        };
        
        this.filters = {
            signalType: 'all', // all, long, short
            shortRsiThreshold: 65,
            longRsiThreshold: 30,
            displayLimit: 100
        };
        
        this.refreshTimer = null;
        this.listeners = {
            dataLoaded: [],
            dataFiltered: [],
            error: []
        };
    }
    
    /**
     * 初始化 API
     */
    async init() {
        this.log('🚀 FilteredSignalsAPI 初始化');
        await this.loadData();
        
        if (this.config.autoRefresh) {
            this.startAutoRefresh();
        }
        
        return this;
    }
    
    /**
     * 加载数据
     */
    async loadData() {
        try {
            this.log('📥 开始获取数据...');
            
            // 1. 获取首页统计数据
            const summaryResponse = await this.request('/api/kline/summary');
            if (summaryResponse.data && summaryResponse.data.data && summaryResponse.data.data.length > 0) {
                const firstRecord = summaryResponse.data.data[0];
                this.data.homepageStats = {
                    todayNewHigh: firstRecord.today_rise_count || 0,
                    todayNewLow: firstRecord.today_crash_count || 0,
                    marketStatus: firstRecord.surge_status || '未知'
                };
                this.log('✅ 首页统计数据:', this.data.homepageStats);
            }
            
            // 2. 获取信号数据
            const fetchLimit = this.filters.displayLimit * 2;
            const timestamp = Date.now();
            const historyResponse = await this.request(
                `/api/filtered-signals/stats?limit=${fetchLimit}&rsi_short_threshold=0&rsi_long_threshold=100&_t=${timestamp}`
            );
            
            if (!historyResponse.data || !historyResponse.data.signals) {
                throw new Error('未获取到有效数据');
            }
            
            this.data.allData = historyResponse.data.signals;
            this.data.lastLoadTime = Date.now();
            this.log(`✅ 获取到 ${this.data.allData.length} 条有效信号数据`);
            
            // 3. 应用过滤
            this.applyFilters();
            
            // 触发回调
            this.trigger('dataLoaded', {
                allData: this.data.allData,
                filteredData: this.data.filteredData,
                stats: this.data.homepageStats
            });
            
            return this.data;
            
        } catch (error) {
            this.error('❌ 加载数据失败:', error);
            this.trigger('error', error);
            throw error;
        }
    }
    
    /**
     * 应用过滤器
     */
    applyFilters() {
        const { signalType, shortRsiThreshold, longRsiThreshold, displayLimit } = this.filters;
        const { allData } = this.data;
        
        this.log('🎯 应用过滤条件:', this.filters);
        
        const debugStats = {
            总数据量: allData.length,
            跳过_超过24小时: 0,
            跳过_无效信号: 0,
            跳过_无效RSI: 0,
            跳过_信号类型不匹配: 0,
            跳过_RSI不符合: 0,
            匹配成功: 0
        };
        
        const VALID_SIGNALS = {
            all: ['抄底做多', '底部做多', '顶部做空'],
            long: ['抄底做多', '底部做多'],
            short: ['顶部做空']
        };
        
        const validSignalList = VALID_SIGNALS[signalType] || VALID_SIGNALS.all;
        const TWENTY_FOUR_HOURS = 24 * 60 * 60 * 1000;
        
        this.data.filteredData = [];
        
        allData.forEach(item => {
            // 0. 过滤超过24小时的信号
            let signalTimeMs = 0;
            
            if (item.time && typeof item.time === 'string') {
                try {
                    const timeStr = item.time.replace(/\//g, '-');
                    signalTimeMs = new Date(timeStr).getTime();
                } catch (e) {
                    this.log('⚠️ 无法解析 time 字段:', item.time, e);
                }
            }
            
            if (!signalTimeMs || isNaN(signalTimeMs)) {
                signalTimeMs = item.open_time || item.created_at || item.crawl_time || 0;
            }
            
            if (signalTimeMs) {
                const now = Date.now();
                const timeDiff = now - signalTimeMs;
                const hours = timeDiff / (1000 * 60 * 60);
                
                if (hours > 24) {
                    debugStats.跳过_超过24小时++;
                    return;
                }
            }
            
            const operationTip = item.operation_tip;
            const rsi1h = parseFloat(item.rsi_1h);
            
            // 1. 验证 operation_tip 是否在有效信号列表中
            if (!validSignalList.includes(operationTip)) {
                debugStats.跳过_无效信号++;
                return;
            }
            
            // 2. 检查 RSI 是否有效
            if (isNaN(rsi1h)) {
                debugStats.跳过_无效RSI++;
                return;
            }
            
            // 3. 根据信号类型应用 RSI 过滤
            if (operationTip === '顶部做空') {
                if (rsi1h < shortRsiThreshold) {
                    debugStats.跳过_RSI不符合++;
                    return;
                }
            } else if (operationTip === '抄底做多' || operationTip === '底部做多') {
                if (rsi1h > longRsiThreshold) {
                    debugStats.跳过_RSI不符合++;
                    return;
                }
            }
            
            debugStats.匹配成功++;
            this.data.filteredData.push(item);
        });
        
        this.log('🔍 过滤调试统计:', debugStats);
        this.log(`✅ 筛选完成，符合条件的信号: ${this.data.filteredData.length}`);
        
        // 排序并限制数量
        this.data.filteredData.sort((a, b) => {
            const timeA = a.created_at || a.crawl_time || 0;
            const timeB = b.created_at || b.crawl_time || 0;
            return timeB - timeA;
        });
        
        if (displayLimit > 0) {
            this.data.filteredData = this.data.filteredData.slice(0, displayLimit);
        }
        
        // 触发回调
        this.trigger('dataFiltered', {
            filteredData: this.data.filteredData,
            stats: debugStats
        });
        
        return this.data.filteredData;
    }
    
    /**
     * 设置过滤器
     */
    setFilters(filters) {
        this.filters = { ...this.filters, ...filters };
        this.log('🔧 更新过滤器:', this.filters);
        return this.applyFilters();
    }
    
    /**
     * 获取数据
     */
    getData() {
        return {
            all: this.data.allData,
            filtered: this.data.filteredData,
            stats: this.data.homepageStats,
            lastUpdate: this.data.lastLoadTime
        };
    }
    
    /**
     * 获取单个信号详情
     */
    getSignal(symbol) {
        return this.data.filteredData.find(item => item.symbol === symbol);
    }
    
    /**
     * 开始自动刷新
     */
    startAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }
        
        this.refreshTimer = setInterval(() => {
            this.log('⏰ 自动刷新触发');
            this.loadData();
        }, this.config.refreshInterval);
        
        this.log(`✅ 自动刷新已启动（${this.config.refreshInterval / 1000}秒间隔）`);
    }
    
    /**
     * 停止自动刷新
     */
    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
            this.log('⏸️ 自动刷新已停止');
        }
    }
    
    /**
     * 销毁实例
     */
    destroy() {
        this.stopAutoRefresh();
        this.data = { allData: [], filteredData: [], homepageStats: null, lastLoadTime: null };
        this.listeners = { dataLoaded: [], dataFiltered: [], error: [] };
        this.log('🗑️ FilteredSignalsAPI 已销毁');
    }
    
    /**
     * 注册事件监听器
     */
    on(event, callback) {
        if (this.listeners[event]) {
            this.listeners[event].push(callback);
        }
        return this;
    }
    
    /**
     * 移除事件监听器
     */
    off(event, callback) {
        if (this.listeners[event]) {
            this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
        }
        return this;
    }
    
    /**
     * 触发事件
     */
    trigger(event, data) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    this.error('事件回调执行失败:', error);
                }
            });
        }
    }
    
    /**
     * HTTP 请求
     */
    async request(url, options = {}) {
        const fullUrl = this.config.apiBaseUrl + url;
        
        if (typeof axios !== 'undefined') {
            // 使用 axios
            return axios.get(fullUrl, {
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                },
                ...options
            });
        } else {
            // 使用 fetch
            const response = await fetch(fullUrl, {
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                },
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            return { data };
        }
    }
    
    /**
     * 日志输出
     */
    log(...args) {
        if (this.config.debug) {
            console.log('[FilteredSignalsAPI]', ...args);
        }
    }
    
    /**
     * 错误输出
     */
    error(...args) {
        console.error('[FilteredSignalsAPI]', ...args);
    }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FilteredSignalsAPI;
}

if (typeof window !== 'undefined') {
    window.FilteredSignalsAPI = FilteredSignalsAPI;
}

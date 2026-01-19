/**
 * 集中API调用管理器
 * 
 * 功能：
 * 1. 请求队列管理 - 避免并发过多
 * 2. 请求限流 - 防止API调用过于频繁
 * 3. 请求优先级 - 重要请求优先处理
 * 4. 请求去重 - 避免重复请求
 * 5. 请求缓存 - 减少不必要的API调用
 * 6. 错误重试 - 自动重试失败请求
 */

class APIManager {
  constructor(options = {}) {
    // 配置参数
    this.maxConcurrent = options.maxConcurrent || 3; // 最大并发请求数
    this.maxQueueSize = options.maxQueueSize || 50; // 最大队列长度
    this.minInterval = options.minInterval || 200; // 最小请求间隔(ms)
    this.cacheTimeout = options.cacheTimeout || 5000; // 缓存超时(ms)
    this.retryAttempts = options.retryAttempts || 2; // 重试次数
    this.retryDelay = options.retryDelay || 1000; // 重试延迟(ms)
    
    // 状态管理
    this.activeRequests = 0; // 当前活跃请求数
    this.requestQueue = []; // 请求队列
    this.lastRequestTime = 0; // 上次请求时间
    this.requestCache = new Map(); // 请求缓存
    this.pendingRequests = new Map(); // 进行中的请求（用于去重）
    
    // 统计信息
    this.stats = {
      total: 0, // 总请求数
      success: 0, // 成功数
      failed: 0, // 失败数
      cached: 0, // 缓存命中数
      queued: 0, // 排队数
      rejected: 0 // 拒绝数
    };
    
    console.log('📡 [API Manager] 初始化完成', {
      maxConcurrent: this.maxConcurrent,
      minInterval: this.minInterval,
      cacheTimeout: this.cacheTimeout
    });
  }
  
  /**
   * 发起API请求
   * @param {Object} config - 请求配置
   * @param {string} config.url - 请求URL
   * @param {string} config.method - 请求方法 (GET/POST/PUT/DELETE)
   * @param {Object} config.params - URL参数
   * @param {Object} config.data - 请求体数据
   * @param {number} config.priority - 优先级 (1-10, 数字越大优先级越高)
   * @param {boolean} config.cache - 是否缓存结果
   * @param {boolean} config.dedupe - 是否去重
   * @param {string} config.tag - 请求标签（用于识别）
   * @returns {Promise} 请求结果
   */
  async request(config) {
    this.stats.total++;
    
    const {
      url,
      method = 'GET',
      params = {},
      data = null,
      priority = 5,
      cache = true,
      dedupe = true,
      tag = 'unknown'
    } = config;
    
    // 生成请求唯一标识
    const requestKey = this.generateRequestKey(url, method, params, data);
    
    // 1. 检查缓存
    if (cache && this.requestCache.has(requestKey)) {
      const cached = this.requestCache.get(requestKey);
      if (Date.now() - cached.timestamp < this.cacheTimeout) {
        console.log(`💾 [API Manager] 缓存命中: ${tag}`, { url });
        this.stats.cached++;
        return Promise.resolve(cached.data);
      } else {
        // 缓存过期，删除
        this.requestCache.delete(requestKey);
      }
    }
    
    // 2. 检查去重（是否有相同请求正在进行）
    if (dedupe && this.pendingRequests.has(requestKey)) {
      console.log(`🔄 [API Manager] 请求去重: ${tag}`, { url });
      return this.pendingRequests.get(requestKey);
    }
    
    // 3. 检查队列是否已满
    if (this.requestQueue.length >= this.maxQueueSize) {
      console.warn(`❌ [API Manager] 队列已满，拒绝请求: ${tag}`, { 
        queueSize: this.requestQueue.length,
        maxSize: this.maxQueueSize
      });
      this.stats.rejected++;
      return Promise.reject(new Error('请求队列已满，请稍后重试'));
    }
    
    // 4. 创建请求Promise
    const requestPromise = new Promise((resolve, reject) => {
      const requestItem = {
        url,
        method,
        params,
        data,
        priority,
        tag,
        requestKey,
        cache,
        resolve,
        reject,
        attempts: 0,
        createdAt: Date.now()
      };
      
      // 加入队列（按优先级排序）
      this.requestQueue.push(requestItem);
      this.requestQueue.sort((a, b) => b.priority - a.priority);
      this.stats.queued++;
      
      console.log(`📥 [API Manager] 请求加入队列: ${tag}`, {
        priority,
        queueSize: this.requestQueue.length,
        activeRequests: this.activeRequests
      });
    });
    
    // 如果启用去重，记录进行中的请求
    if (dedupe) {
      this.pendingRequests.set(requestKey, requestPromise);
      requestPromise.finally(() => {
        this.pendingRequests.delete(requestKey);
      });
    }
    
    // 5. 触发队列处理
    this.processQueue();
    
    return requestPromise;
  }
  
  /**
   * 处理请求队列
   */
  async processQueue() {
    // 检查是否可以处理新请求
    if (this.activeRequests >= this.maxConcurrent) {
      console.log(`⏳ [API Manager] 达到并发上限 (${this.activeRequests}/${this.maxConcurrent})`);
      return;
    }
    
    if (this.requestQueue.length === 0) {
      return;
    }
    
    // 检查是否需要限流
    const now = Date.now();
    const timeSinceLastRequest = now - this.lastRequestTime;
    if (timeSinceLastRequest < this.minInterval) {
      const delay = this.minInterval - timeSinceLastRequest;
      console.log(`⏱️ [API Manager] 限流延迟 ${delay}ms`);
      setTimeout(() => this.processQueue(), delay);
      return;
    }
    
    // 从队列取出一个请求
    const requestItem = this.requestQueue.shift();
    if (!requestItem) return;
    
    this.activeRequests++;
    this.lastRequestTime = Date.now();
    
    console.log(`🚀 [API Manager] 开始处理请求: ${requestItem.tag}`, {
      url: requestItem.url,
      priority: requestItem.priority,
      activeRequests: this.activeRequests,
      queueRemaining: this.requestQueue.length
    });
    
    try {
      // 执行实际的HTTP请求
      const result = await this.executeRequest(requestItem);
      
      // 成功：缓存结果
      if (requestItem.cache) {
        this.requestCache.set(requestItem.requestKey, {
          data: result,
          timestamp: Date.now()
        });
      }
      
      this.stats.success++;
      requestItem.resolve(result);
      
      console.log(`✅ [API Manager] 请求成功: ${requestItem.tag}`, {
        url: requestItem.url,
        duration: Date.now() - requestItem.createdAt
      });
      
    } catch (error) {
      // 失败：检查是否需要重试
      requestItem.attempts++;
      
      if (requestItem.attempts < this.retryAttempts) {
        console.warn(`🔄 [API Manager] 请求失败，准备重试 (${requestItem.attempts}/${this.retryAttempts}): ${requestItem.tag}`, {
          url: requestItem.url,
          error: error.message
        });
        
        // 延迟后重新加入队列
        setTimeout(() => {
          this.requestQueue.unshift(requestItem); // 优先重试
          this.processQueue();
        }, this.retryDelay);
        
      } else {
        this.stats.failed++;
        requestItem.reject(error);
        
        console.error(`❌ [API Manager] 请求失败: ${requestItem.tag}`, {
          url: requestItem.url,
          attempts: requestItem.attempts,
          error: error.message
        });
      }
    } finally {
      this.activeRequests--;
      
      // 继续处理队列中的下一个请求
      if (this.requestQueue.length > 0) {
        setTimeout(() => this.processQueue(), this.minInterval);
      }
    }
  }
  
  /**
   * 执行实际的HTTP请求
   */
  async executeRequest(requestItem) {
    const { url, method, params, data } = requestItem;
    
    const config = {
      url,
      method,
      params,
      data,
      timeout: 30000 // 30秒超时
    };
    
    const response = await axios(config);
    return response.data;
  }
  
  /**
   * 生成请求唯一标识
   */
  generateRequestKey(url, method, params, data) {
    const paramsStr = JSON.stringify(params || {});
    const dataStr = JSON.stringify(data || {});
    return `${method}:${url}:${paramsStr}:${dataStr}`;
  }
  
  /**
   * 清空缓存
   */
  clearCache() {
    const size = this.requestCache.size;
    this.requestCache.clear();
    console.log(`🗑️ [API Manager] 清空缓存: ${size} 条记录`);
  }
  
  /**
   * 清空队列
   */
  clearQueue() {
    const size = this.requestQueue.length;
    this.requestQueue.forEach(item => {
      item.reject(new Error('队列已清空'));
    });
    this.requestQueue = [];
    console.log(`🗑️ [API Manager] 清空队列: ${size} 个请求`);
  }
  
  /**
   * 获取统计信息
   */
  getStats() {
    return {
      ...this.stats,
      activeRequests: this.activeRequests,
      queueSize: this.requestQueue.length,
      cacheSize: this.requestCache.size,
      successRate: this.stats.total > 0 
        ? ((this.stats.success / this.stats.total) * 100).toFixed(2) + '%'
        : 'N/A'
    };
  }
  
  /**
   * 打印统计信息
   */
  printStats() {
    const stats = this.getStats();
    console.table(stats);
  }
}

// 创建全局单例
window.apiManager = new APIManager({
  maxConcurrent: 3, // 最大并发3个请求
  minInterval: 200, // 请求间隔至少200ms
  cacheTimeout: 5000, // 缓存5秒
  retryAttempts: 2 // 失败重试2次
});

console.log('✅ [API Manager] 全局实例已创建: window.apiManager');

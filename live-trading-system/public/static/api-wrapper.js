/**
 * 简化版API包装器 - 用于K线查询页面
 * 提供统一的API调用接口，兼容不同响应格式
 */

// API优先级常量
const API_PRIORITY = {
  URGENT: 10,  // 紧急
  HIGH: 8,     // 高
  NORMAL: 5,   // 普通
  LOW: 3,      // 低
  BACKGROUND: 1 // 后台
};

// API包装器对象
const API = {
  /**
   * GET请求
   * @param {string} url - 请求URL
   * @param {Object} options - 请求选项
   * @param {number} options.priority - 优先级（可选）
   * @param {boolean} options.cache - 是否缓存（可选）
   * @returns {Promise<{data: any}>} 统一格式的响应
   */
  async get(url, options = {}) {
    try {
      console.log(`📡 [API] GET请求:`, url, options);
      
      // 如果存在全局apiManager，使用它
      if (window.apiManager) {
        const result = await window.apiManager.request({
          url,
          method: 'GET',
          priority: options.priority || API_PRIORITY.NORMAL,
          cache: options.cache !== false,
          tag: `GET ${url}`
        });
        
        // apiManager返回的result就是response.data
        console.log(`✅ [API] GET成功 (通过apiManager):`, url, '数据:', result);
        return { data: result };
      }
      
      // 降级方案：直接使用axios
      const response = await axios.get(url);
      console.log(`✅ [API] GET成功 (通过axios):`, url, '数据:', response.data);
      return { data: response.data };
      
    } catch (error) {
      console.error(`❌ [API] GET失败:`, url, error);
      throw error;
    }
  },
  
  /**
   * POST请求
   * @param {string} url - 请求URL
   * @param {any} data - 请求体数据
   * @param {Object} options - 请求选项
   * @param {number} options.priority - 优先级（可选）
   * @returns {Promise<{data: any}>} 统一格式的响应
   */
  async post(url, data = null, options = {}) {
    try {
      console.log(`📡 [API] POST请求:`, url, '数据:', data, '选项:', options);
      
      // 如果存在全局apiManager，使用它
      if (window.apiManager) {
        const result = await window.apiManager.request({
          url,
          method: 'POST',
          data,
          priority: options.priority || API_PRIORITY.NORMAL,
          cache: false, // POST请求默认不缓存
          tag: `POST ${url}`
        });
        
        console.log(`✅ [API] POST成功 (通过apiManager):`, url, '响应:', result);
        return { data: result };
      }
      
      // 降级方案：直接使用axios
      const response = await axios.post(url, data);
      console.log(`✅ [API] POST成功 (通过axios):`, url, '响应:', response.data);
      return { data: response.data };
      
    } catch (error) {
      console.error(`❌ [API] POST失败:`, url, error);
      throw error;
    }
  }
};

console.log('✅ [API Wrapper] API包装器已加载，提供统一的API调用接口');
console.log('📌 [API Wrapper] 支持优先级:', API_PRIORITY);
console.log('🔍 [API Wrapper] apiManager存在:', !!window.apiManager);

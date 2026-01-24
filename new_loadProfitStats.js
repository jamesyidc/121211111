        // 数据缓存对象（按日期缓存）
        const profitDataCache = {};
        
        async function loadProfitStats() {
            console.log('🚀 开始加载空单盈利统计数据（按需分页）...');
            
            // 确保图表已初始化
            initCharts();
            
            // 加载今天的数据
            const today = new Date();
            const todayStr = formatDate(today);
            
            console.log(`📅 加载今天的数据: ${todayStr}`);
            
            await loadDayData(todayStr);
            currentPage = 0;
            renderProfitStatsChart(currentPage);
        }
        
        // 辅助函数：格式化日期为 YYYY-MM-DD
        function formatDate(date) {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        }
        
        // 加载指定日期的数据
        async function loadDayData(dateStr) {
            // 如果已经缓存，直接返回
            if (profitDataCache[dateStr]) {
                console.log(`✅ 使用缓存数据: ${dateStr}`);
                return profitDataCache[dateStr];
            }
            
            console.log(`📡 从服务器加载数据: ${dateStr}`);
            
            try {
                const response = await fetch(`/api/anchor-system/profit-history?date=${dateStr}&trade_mode=real`);
                const result = await response.json();
                
                if (result.success && result.history) {
                    profitDataCache[dateStr] = result.history;
                    console.log(`✅ 数据加载成功: ${dateStr}, 记录数: ${result.history.length}`);
                    
                    // 更新更新时间
                    if (result.history.length > 0) {
                        const latestData = result.history[result.history.length - 1];
                        document.getElementById('profitStatsUpdateTime').textContent = 
                            `最后更新: ${latestData.datetime}`;
                    }
                    
                    return result.history;
                } else {
                    console.warn(`⚠️ ${dateStr} 暂无数据`);
                    profitDataCache[dateStr] = [];
                    return [];
                }
            } catch (error) {
                console.error(`❌ 加载 ${dateStr} 数据失败:`, error);
                return [];
            }
        }
        
        // 翻页函数（修改为按需加载）
        async function changeProfitStatsPage(direction) {
            currentPage += direction;
            
            // 限制翻页范围（最多往前翻30天）
            if (currentPage < -29) {
                currentPage = -29;
                alert('⚠️ 最多只能查看30天内的数据');
                return;
            }
            if (currentPage > 0) {
                currentPage = 0;
                alert('⚠️ 已经是最新数据了');
                return;
            }
            
            // 计算目标日期
            const targetDate = new Date();
            targetDate.setDate(targetDate.getDate() + currentPage);
            const targetDateStr = formatDate(targetDate);
            
            console.log(`📖 翻页到: ${targetDateStr} (偏移: ${currentPage}天)`);
            
            // 加载目标日期的数据（如果未缓存）
            await loadDayData(targetDateStr);
            
            // 渲染图表
            renderProfitStatsChart(currentPage);
        }
        
        // 渲染多空单盈利统计图表（修改为从缓存读取）
        function renderProfitStatsChart(pageOffset) {
            console.log(`📈 渲染图表，页码偏移: ${pageOffset}天`);
            
            // 确保图表已初始化
            if (!profitStatsChart) {
                console.error('❌ profitStatsChart 未初始化，尝试重新初始化...');
                initCharts();
                if (!profitStatsChart) {
                    console.error('❌ profitStatsChart 初始化失败，无法渲染图表');
                    return;
                }
            }
            
            // 计算目标日期
            const targetDate = new Date();
            targetDate.setDate(targetDate.getDate() + pageOffset);
            const targetDateStr = formatDate(targetDate);
            
            // 从缓存获取数据
            const dayData = profitDataCache[targetDateStr] || [];
            
            if (dayData.length === 0) {
                console.warn(`⚠️ ${targetDateStr} 无数据可显示`);
                // 显示空数据图表
                profitStatsChart.setOption({
                    title: {
                        text: `${targetDateStr} 多空单盈利统计`,
                        subtext: '暂无数据',
                        left: 'center',
                        top: 20,
                        textStyle: { color: '#333', fontSize: 18, fontWeight: 'bold' }
                    },
                    xAxis: { data: [] },
                    series: [
                        { name: '空单≥80%', data: [] },
                        { name: '空单≥120%', data: [] },
                        { name: '多单≤40%', data: [] },
                        { name: '多单亏损', data: [] }
                    ]
                });
                return;
            }
            
            console.log(`📊 渲染 ${targetDateStr} 数据，共 ${dayData.length} 条记录`);
            
            // 提取图表数据（原有逻辑保持不变，但使用 dayData 而不是 allHistoryData）
            const timestamps = [];
            const shortGte80 = [];
            const shortGte120 = [];
            const longLte40 = [];
            const longLoss = [];
            
            for (const record of dayData) {
                const dt = new Date(record.timestamp * 1000);
                const timeStr = `${String(dt.getHours()).padStart(2, '0')}:${String(dt.getMinutes()).padStart(2, '0')}`;
                timestamps.push(timeStr);
                
                const stats = record.stats || {};
                shortGte80.push(stats.short?.gte_80 || 0);
                shortGte120.push(stats.short?.gte_120 || 0);
                longLte40.push(stats.long?.lte_40 || 0);
                longLoss.push(stats.long?.loss || 0);
            }
            
            // 渲染图表（原有配置保持不变，只修改标题）
            profitStatsChart.setOption({
                title: {
                    text: `${targetDateStr} 多空单盈利统计`,
                    subtext: `共 ${dayData.length} 条记录`,
                    left: 'center',
                    top: 20,
                    textStyle: { color: '#333', fontSize: 18, fontWeight: 'bold' }
                },
                tooltip: {
                    trigger: 'axis',
                    axisPointer: { type: 'cross' }
                },
                legend: {
                    data: ['空单≥80%', '空单≥120%', '多单≤40%', '多单亏损'],
                    top: 60
                },
                grid: {
                    left: '3%',
                    right: '4%',
                    bottom: '3%',
                    containLabel: true
                },
                xAxis: {
                    type: 'category',
                    boundaryGap: false,
                    data: timestamps
                },
                yAxis: {
                    type: 'value'
                },
                series: [
                    {
                        name: '空单≥80%',
                        type: 'line',
                        data: shortGte80,
                        smooth: true,
                        itemStyle: { color: '#10b981' }
                    },
                    {
                        name: '空单≥120%',
                        type: 'line',
                        data: shortGte120,
                        smooth: true,
                        itemStyle: { color: '#3b82f6' }
                    },
                    {
                        name: '多单≤40%',
                        type: 'line',
                        data: longLte40,
                        smooth: true,
                        itemStyle: { color: '#f59e0b' }
                    },
                    {
                        name: '多单亏损',
                        type: 'line',
                        data: longLoss,
                        smooth: true,
                        itemStyle: { color: '#ef4444' }
                    }
                ]
            });
            
            console.log('✅ 图表渲染完成');
        }

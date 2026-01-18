# Google Drive TXT 检测器 - 使用说明

## 📋 功能概述

本系统实现了从Google Drive自动检测、下载并导入TXT文件的功能，支持跨日期自动切换文件夹。

## 🎯 主要功能

### 1. 跨日期文件夹自动切换
- **单数日期**（1, 3, 5, 7, 9...）使用单数父文件夹
- **双数日期**（2, 4, 6, 8, 10...）使用双数父文件夹
- 每天 00:10 自动清理非当日的父文件夹配置
- 自动查找当日子文件夹（格式: YYYY-MM-DD）

### 2. TXT文件监控
- 实时监控指定文件夹中的TXT文件
- 自动下载最新的TXT文件
- 解析文件内容并导入数据库
- 支持30秒自动检查间隔

### 3. 数据导入
- 自动解析TXT文件格式
- 导入到 `crypto_snapshots` 表
- 支持的字段：
  - symbol: 币种符号
  - price: 价格
  - change_24h: 24小时涨跌幅
  - volume_24h: 24小时交易量
  - escape_24h_count: 24小时逃顶信号数
  - escape_2h_count: 2小时逃顶信号数
  - rise_strength: 上涨强度
  - decline_strength: 下跌强度
  - trend: 趋势
  - signal: 信号
  - snapshot_time: 快照时间

## 🚀 快速开始

### 步骤 1: 配置父文件夹

访问配置页面: https://5000-igsydcyqs9jlcot56rnqk-8f57ffe2.sandbox.novita.ai/gdrive-config

1. **单数日期父文件夹**：输入单数日期使用的Google Drive文件夹共享链接
2. **双数日期父文件夹**：输入双数日期使用的Google Drive文件夹共享链接

父文件夹链接格式：
```
https://drive.google.com/drive/folders/FOLDER_ID?usp=sharing
```

系统会自动：
- 提取文件夹ID
- 查找当天日期的子文件夹（如：2026-01-05）
- 验证子文件夹中是否包含TXT文件
- 保存配置

### 步骤 2: 启动检测器

有两种方式启动检测器：

#### 方式1: PM2管理（推荐）
```bash
# 启动检测器
pm2 start gdrive_final_detector.py --name gdrive-detector --interpreter python3

# 查看状态
pm2 status

# 查看日志
pm2 logs gdrive-detector

# 停止检测器
pm2 stop gdrive-detector

# 重启检测器
pm2 restart gdrive-detector
```

#### 方式2: 直接运行
```bash
# 前台运行（调试用）
python3 gdrive_final_detector.py

# 后台运行
nohup python3 gdrive_final_detector.py > /dev/null 2>&1 &
```

### 步骤 3: 监控状态

访问监控页面: https://5000-igsydcyqs9jlcot56rnqk-8f57ffe2.sandbox.novita.ai/gdrive-detector

页面显示：
- ✅ 检测器运行状态
- 📄 文件时间戳
- ⏱️ 数据延迟
- 🔢 检查次数
- 📁 当前使用的文件夹ID
- 📂 今日TXT文件列表
- 📋 实时日志

## 📂 文件夹结构要求

Google Drive文件夹结构应该如下：

```
父文件夹（单数日）/
  ├── 2026-01-01/
  │   ├── 2026-01-01_0800.txt
  │   ├── 2026-01-01_0830.txt
  │   └── 2026-01-01_0900.txt
  ├── 2026-01-03/
  │   ├── 2026-01-03_0800.txt
  │   └── 2026-01-03_0830.txt
  └── 2026-01-05/
      └── 2026-01-05_0800.txt

父文件夹（双数日）/
  ├── 2026-01-02/
  │   └── 2026-01-02_0800.txt
  ├── 2026-01-04/
  │   └── 2026-01-04_0800.txt
  └── 2026-01-06/
      └── 2026-01-06_0800.txt
```

### TXT文件命名规则
- 格式：`YYYY-MM-DD_HHMM.txt`
- 例如：`2026-01-05_0800.txt` 表示 2026年1月5日 08:00 的数据

### TXT文件内容格式
每行一条记录，字段用逗号分隔：
```
symbol,price,change_24h,volume_24h,escape_24h,escape_2h,rise,decline,trend,signal
BTC-USDT-SWAP,91115.6,1.31,1234567890,523,12,2.5,-1.2,上涨,买入
ETH-USDT-SWAP,3456.78,-0.5,987654321,234,5,1.2,-2.3,下跌,观望
```

## 🔧 配置文件说明

配置文件位置: `/home/user/webapp/daily_folder_config.json`

```json
{
  "parent_folder_url": "https://drive.google.com/drive/folders/...",
  "parent_folder_id": "FOLDER_ID",
  "current_date": "2026-01-05",
  "data_date": "2026-01-05",
  "folder_id": "TODAY_SUBFOLDER_ID",
  "folder_name": "2026-01-05",
  "latest_txt": "2026-01-05_0930.txt",
  "txt_count": 15,
  "last_update": "2026-01-05 09:35:00",
  "update_reason": "自动跨日期切换",
  "root_folder_odd": "ODD_DATE_PARENT_FOLDER_ID",
  "root_folder_even": "EVEN_DATE_PARENT_FOLDER_ID",
  "last_imported_file": "2026-01-05_0930.txt",
  "last_import_time": "2026-01-05 09:35:00",
  "last_import_records": 27
}
```

### 配置字段说明

| 字段 | 说明 |
|------|------|
| `parent_folder_url` | 当前使用的父文件夹共享链接 |
| `parent_folder_id` | 当前使用的父文件夹ID |
| `current_date` | 当前日期 |
| `data_date` | 数据日期 |
| `folder_id` | 今日子文件夹ID |
| `folder_name` | 今日子文件夹名称 |
| `latest_txt` | 最新的TXT文件名 |
| `txt_count` | TXT文件数量 |
| `last_update` | 最后更新时间 |
| `update_reason` | 更新原因 |
| `root_folder_odd` | 单数日期父文件夹ID |
| `root_folder_even` | 双数日期父文件夹ID |
| `last_imported_file` | 最后导入的文件 |
| `last_import_time` | 最后导入时间 |
| `last_import_records` | 最后导入记录数 |

## 📊 数据库表结构

表名: `crypto_snapshots`

```sql
CREATE TABLE crypto_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    price REAL NOT NULL,
    change_24h REAL NOT NULL,
    volume_24h REAL NOT NULL,
    escape_24h_count INTEGER NOT NULL,
    escape_2h_count INTEGER NOT NULL,
    rise_strength REAL NOT NULL,
    decline_strength REAL NOT NULL,
    trend TEXT NOT NULL,
    signal TEXT NOT NULL,
    snapshot_time TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, snapshot_time)
);
```

## 🔌 API 接口

### 1. 获取检测器状态
```
GET /api/gdrive-detector/status
```

返回：
```json
{
  "success": true,
  "data": {
    "detector_running": true,
    "file_timestamp": "2026-01-05 09:30:00",
    "delay_minutes": 5.2,
    "check_count": 123,
    "last_check_time": "2026-01-05 09:35:00",
    "current_time": "2026-01-05 09:35:00",
    "folder_id": "TODAY_FOLDER_ID",
    "root_folder_odd": "ODD_FOLDER_ID",
    "root_folder_even": "EVEN_FOLDER_ID",
    "today_date": "2026年01月05日"
  }
}
```

### 2. 获取今日TXT文件列表
```
GET /api/gdrive-detector/txt-files
```

返回：
```json
{
  "success": true,
  "files": [
    "2026-01-05_0930.txt",
    "2026-01-05_0900.txt",
    "2026-01-05_0830.txt"
  ],
  "count": 3,
  "date": "2026-01-05",
  "folder_id": "FOLDER_ID"
}
```

### 3. 获取配置
```
GET /api/gdrive-detector/config
```

返回：
```json
{
  "success": true,
  "config": {
    "current_date": "2026-01-05",
    "folder_id": "FOLDER_ID",
    "latest_txt": "2026-01-05_0930.txt",
    ...
  }
}
```

### 4. 更新配置
```
POST /api/gdrive-detector/config
Content-Type: application/json

{
  "parent_folder_url": "https://drive.google.com/drive/folders/FOLDER_ID"
}
```

返回：
```json
{
  "success": true,
  "message": "配置更新成功",
  "data": {
    "parent_folder_id": "PARENT_FOLDER_ID",
    "today_folder_id": "TODAY_FOLDER_ID",
    "today_date": "2026-01-05",
    "txt_count": 15,
    "latest_txt": "2026-01-05_0930.txt",
    "is_odd_day": true
  }
}
```

### 5. 手动触发更新
```
POST /api/gdrive-detector/trigger-update
```

返回：
```json
{
  "success": true,
  "message": "检测已执行",
  "output": "...",
  "error": ""
}
```

## 📋 日志说明

日志文件位置: `/home/user/webapp/gdrive_final_detector.log`

日志格式：
```
[2026-01-05 09:35:00] 🔍 检查 #123 - 2026-01-05 09:35:00
[2026-01-05 09:35:01] 📄 最新文件已导入: 2026-01-05_0930.txt
[2026-01-05 09:35:01] ✅ 检查完成
[2026-01-05 09:35:01] ⏱️ 等待 30 秒...
```

日志级别：
- 🚀 启动信息
- 🔍 检查信息
- 📅 日期变化
- 📥 文件导入
- 📊 数据解析
- ✅ 成功信息
- ⚠️ 警告信息
- ❌ 错误信息

查看实时日志：
```bash
# 查看最后50行
tail -f -n 50 /home/user/webapp/gdrive_final_detector.log

# 查看所有日志
cat /home/user/webapp/gdrive_final_detector.log
```

## 🐛 故障排除

### 问题1: 检测器未运行
**解决方法**:
```bash
# 检查进程
ps aux | grep gdrive_final_detector.py

# 重启检测器
pm2 restart gdrive-detector

# 或手动启动
python3 /home/user/webapp/gdrive_final_detector.py
```

### 问题2: 找不到今日文件夹
**可能原因**:
- 父文件夹ID配置错误
- Google Drive中没有创建今日文件夹
- 文件夹名称格式不正确（应为YYYY-MM-DD）

**解决方法**:
1. 检查配置: 访问 `/gdrive-config` 页面
2. 验证Google Drive文件夹结构
3. 手动创建今日文件夹（格式：YYYY-MM-DD）

### 问题3: 无法下载TXT文件
**可能原因**:
- Google Drive共享权限不足
- 网络连接问题
- 文件ID提取失败

**解决方法**:
1. 确保文件夹共享权限为"任何拥有链接的人"
2. 检查网络连接
3. 查看日志获取详细错误信息

### 问题4: 数据导入失败
**可能原因**:
- TXT文件格式不正确
- 数据库权限问题
- 字段解析错误

**解决方法**:
1. 检查TXT文件格式是否符合规范
2. 确保数据库文件有写权限
3. 查看日志中的详细错误信息

## 📈 性能优化建议

1. **检查间隔**: 默认30秒，可根据需要调整 `CHECK_INTERVAL` 变量
2. **日志文件**: 定期清理日志文件以节省磁盘空间
3. **数据库索引**: 为常用查询字段添加索引
4. **并发控制**: 避免多个检测器实例同时运行

## 🔒 安全建议

1. **文件夹权限**: 只设置必要的共享权限
2. **配置文件**: 定期备份配置文件
3. **数据库备份**: 定期备份数据库
4. **日志监控**: 监控异常日志和错误信息

## 📞 技术支持

如遇到问题：
1. 查看实时日志: `/gdrive-detector`
2. 检查配置: `/gdrive-config`
3. 查看API状态: `/api/gdrive-detector/status`
4. 查看数据库日志

---

**最后更新**: 2026-01-05  
**版本**: v1.0  
**状态**: ✅ 生产就绪

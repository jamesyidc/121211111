#!/usr/bin/env python3
"""
Google Drive TXT文件检测器 - JSONL版本
自动跨日期文件夹更新 + JSONL数据存储
"""
import os
import sys
sys.path.append('/home/user/webapp/source_code')

import json
import time
import re
import requests
from datetime import datetime
import pytz
from gdrive_jsonl_manager import GDriveJSONLManager
from txt_parser_enhanced import parse_txt_file_enhanced
from aggregate_jsonl_manager import AggregateJSONLManager
from priority_calculator import calculate_priority_and_score, calculate_count_score

# 配置
CONFIG_FILE = '/home/user/webapp/daily_folder_config.json'
LOG_FILE = '/home/user/webapp/gdrive_detector_jsonl.log'
CHECK_INTERVAL = 30  # 秒

# JSONL管理器
jsonl_manager = GDriveJSONLManager()
aggregate_manager = AggregateJSONLManager()

def log_message(message):
    """记录日志"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}\n"
    
    print(log_line, end='')
    
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_line)
    except Exception as e:
        print(f"写入日志失败: {e}")

def load_config():
    """加载配置"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log_message(f"❌ 加载配置失败: {e}")
        return {}

def save_config(config):
    """保存配置"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        log_message(f"❌ 保存配置失败: {e}")
        return False

def get_beijing_time():
    """获取北京时间"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    return datetime.now(beijing_tz)

def find_today_folder(parent_folder_id, today_str):
    """在父文件夹中查找今天的子文件夹"""
    try:
        url = f"https://drive.google.com/embeddedfolderview?id={parent_folder_id}"
        response = requests.get(url, timeout=10)
        content = response.text
        
        # 查找今日日期文件夹
        if today_str not in content:
            return None, f"父文件夹中未找到日期: {today_str}"
        
        # 查找日期出现的位置
        idx = content.find(today_str)
        if idx == -1:
            return None, f"无法定位日期: {today_str}"
        
        # 向前搜索500个字符，找到最近的文件夹链接
        search_start = max(0, idx - 500)
        search_text = content[search_start:idx + 50]
        
        # 提取文件夹链接: /drive/folders/ID
        folder_pattern = r'/drive/folders/([A-Za-z0-9_-]{25,})'
        matches = re.findall(folder_pattern, search_text)
        
        if matches:
            # 取最后一个匹配（最接近日期的）
            folder_id = matches[-1]
            log_message(f"   找到候选ID: {folder_id}")
            
            # 验证这个文件夹是否包含今日的TXT文件
            test_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
            test_response = requests.get(test_url, timeout=10)
            
            if test_response.status_code == 200:
                # 检查是否包含今日日期的TXT文件
                txt_pattern = rf'>{today_str}_\d{{4}}\.txt<'
                if re.search(txt_pattern, test_response.text):
                    log_message(f"   验证通过，包含今日TXT文件")
                    return folder_id, None
                else:
                    log_message(f"   验证失败，不包含今日TXT文件")
        
        return None, f"无法提取或验证文件夹ID for {today_str}"
        
    except Exception as e:
        return None, f"查找文件夹失败: {e}"

def get_txt_files(folder_id, date_str):
    """获取指定文件夹中的TXT文件列表"""
    try:
        url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
        response = requests.get(url, timeout=10)
        content = response.text
        
        # 查找TXT文件
        pattern = rf'>{date_str}_(\d{{4}})\.txt<'
        matches = re.findall(pattern, content)
        
        if matches:
            # 排序（从新到旧）
            times_sorted = sorted(matches, reverse=True)
            return [f"{date_str}_{time}.txt" for time in times_sorted], None
        else:
            return [], None
            
    except Exception as e:
        return [], f"获取文件列表失败: {e}"

def download_txt_file(folder_id, filename):
    """下载TXT文件内容"""
    try:
        # 获取文件ID
        url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
        response = requests.get(url, timeout=10)
        content = response.text
        
        # 新的匹配模式：查找所有 entry 并匹配 title
        entries = re.findall(r'id="entry-([A-Za-z0-9_-]+)".*?<div class="flip-entry-title">([^<]+)</div>', content, re.DOTALL)
        
        file_id = None
        for entry_id, title in entries:
            if title == filename:
                file_id = entry_id
                break
        
        if not file_id:
            return None, f"找不到文件ID: {filename}"
        
        log_message(f"   找到文件ID: {file_id}")
        
        # 下载文件
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        file_response = requests.get(download_url, timeout=30)
        
        if file_response.status_code == 200:
            return file_response.text, None
        else:
            return None, f"下载失败: HTTP {file_response.status_code}"
            
    except Exception as e:
        return None, f"下载文件失败: {e}"

def parse_txt_content(content, snapshot_time):
    """解析TXT文件内容
    
    文件格式：
    1|BTC|0.11|0|0|2026-01-05 15:08:15|126259.48|2025-10-07|-26.6|1.38|||13|91098.9|72.66%|111.97%
    
    字段映射：
    [1]: inst_id (币种)
    [3]: rush_up (急涨)
    [4]: rush_down (急跌)
    [5]: snapshot_time (快照时间)
    [6]: last_price (最新价格)
    [8]: change_24h (24h涨跌幅)
    [12]: count (计次)
    [13]: vol_24h (24h交易量)
    """
    try:
        records = []
        lines = content.strip().split('\n')
        
        # 找到数据开始标记
        start_index = -1
        for i, line in enumerate(lines):
            if '[超级列表框_首页开始]' in line or '[超级列表框_首页开始]' in line.strip('\r'):
                start_index = i + 1
                break
        
        if start_index == -1:
            log_message("⚠️ 未找到数据开始标记，从第一行开始解析")
            start_index = 0
        
        # 解析每一行
        for line in lines[start_index:]:
            line = line.strip().strip('\r')
            
            if not line or line.startswith('#') or line.startswith('透明标签') or '[' in line:
                continue
            
            parts = line.split('|')
            if len(parts) < 14:
                continue
            
            try:
                inst_id = parts[1].strip()
                if not inst_id:
                    continue
                
                # 提取数据
                last_price = float(parts[6]) if parts[6] else 0.0
                change_24h = float(parts[8].replace('%', '')) if parts[8] and parts[8] != 'NaN' else 0.0
                vol_24h = float(parts[13]) if parts[13] else 0.0
                rush_up = int(parts[3]) if parts[3] else 0
                rush_down = int(parts[4]) if parts[4] else 0
                count = int(parts[12]) if parts[12] else 0
                
                # 计算diff和status
                diff = rush_up - rush_down
                if diff > 0:
                    status = '急涨'
                elif diff < 0:
                    status = '急跌'
                else:
                    status = '平稳'
                
                # 提取日期
                snapshot_date = snapshot_time.split()[0] if ' ' in snapshot_time else snapshot_time
                
                record = {
                    'snapshot_date': snapshot_date,
                    'snapshot_time': snapshot_time,
                    'inst_id': inst_id,
                    'last_price': last_price,
                    'vol_24h': vol_24h,
                    'rush_up': rush_up,
                    'rush_down': rush_down,
                    'diff': diff,
                    'count': count,
                    'status': status,
                    'change_24h': change_24h,
                    'created_at': datetime.now().isoformat(),
                    'high_24h': None,
                    'low_24h': None,
                    'count_score_display': None,
                    'count_score_type': None
                }
                
                records.append(record)
                
            except (ValueError, IndexError) as e:
                log_message(f"  ⚠️ 解析行失败: {line[:50]}... - {e}")
                continue
        
        return records, None
        
    except Exception as e:
        return [], f"解析内容失败: {e}"

def save_to_jsonl(records):
    """保存记录到JSONL"""
    try:
        # 使用upsert模式（基于inst_id和snapshot_time唯一性）
        jsonl_manager.upsert_snapshots(records)
        return len(records), None
    except Exception as e:
        return 0, f"保存到JSONL失败: {e}"

def check_and_update_folder():
    """检查并更新文件夹ID（如果需要）"""
    try:
        config = load_config()
        
        if 'parent_folder_id' not in config:
            log_message("❌ 配置中缺少parent_folder_id")
            return False
        
        parent_folder_id = config['parent_folder_id']
        beijing_time = get_beijing_time()
        today_str = beijing_time.strftime('%Y-%m-%d')
        current_folder_date = config.get('current_folder_date', '')
        
        # 检查是否需要更新
        if current_folder_date == today_str:
            # 日期未变，无需更新
            return True
        
        log_message(f"📅 检测到日期变化: {current_folder_date} → {today_str}")
        log_message(f"🔍 开始查找今日文件夹...")
        
        # 查找今天的文件夹
        folder_id, error = find_today_folder(parent_folder_id, today_str)
        
        if error:
            log_message(f"❌ {error}")
            return False
        
        if folder_id:
            log_message(f"✅ 找到今日文件夹: {folder_id}")
            
            # 更新配置
            config['current_folder_id'] = folder_id
            config['current_folder_date'] = today_str
            config['last_update_time'] = beijing_time.strftime('%Y-%m-%d %H:%M:%S')
            
            if save_config(config):
                log_message(f"✅ 配置已更新")
                return True
            else:
                log_message(f"❌ 保存配置失败")
                return False
        else:
            log_message(f"⚠️  未找到今日文件夹")
            return False
            
    except Exception as e:
        log_message(f"❌ 检查更新失败: {e}")
        return False

def process_new_files():
    """处理新文件"""
    try:
        config = load_config()
        
        if 'current_folder_id' not in config:
            log_message("❌ 配置中缺少current_folder_id")
            return False
        
        folder_id = config['current_folder_id']
        beijing_time = get_beijing_time()
        today_str = beijing_time.strftime('%Y-%m-%d')
        
        # 获取TXT文件列表
        txt_files, error = get_txt_files(folder_id, today_str)
        
        if error:
            log_message(f"❌ {error}")
            return False
        
        if not txt_files:
            log_message("   暂无TXT文件")
            return True
        
        # 获取最新快照时间
        latest_snapshot_time = jsonl_manager.get_latest_snapshot_time()
        log_message(f"   当前最新快照: {latest_snapshot_time}")
        log_message(f"   发现 {len(txt_files)} 个文件")
        
        # 处理新文件
        processed_count = 0
        for txt_file in txt_files:
            # 从文件名提取时间
            time_part = txt_file.replace('.txt', '').split('_')[1]  # 例如 "1530"
            file_time = f"{today_str} {time_part[:2]}:{time_part[2:]}:00"
            
            # 检查是否已处理
            if latest_snapshot_time and file_time <= latest_snapshot_time:
                continue
            
            log_message(f"\n📄 处理文件: {txt_file} (时间: {file_time})")
            
            # 下载文件
            content, error = download_txt_file(folder_id, txt_file)
            if error:
                log_message(f"  ❌ {error}")
                continue
            
            # 解析内容（使用增强版解析器）
            aggregate_data, coin_records, error = parse_txt_file_enhanced(content, file_time)
            if error:
                log_message(f"  ❌ {error}")
                continue
            
            log_message(f"  📊 解析到 {len(coin_records)} 条币种记录")
            
            # 检查记录数量是否异常
            if len(coin_records) < 20:  # 正常应该有29条左右
                log_message(f"  ⚠️  警告: 只解析到 {len(coin_records)} 条记录 (预期约29条)")
                log_message(f"      TXT文件可能不完整，请检查Windows客户端！")
                log_message(f"      聚合数据: 急涨={aggregate_data.get('rush_up_total', 0)}, "
                          f"急跌={aggregate_data.get('rush_down_total', 0)}")
            
            # 为每条币种记录计算优先级和计次得分
            for record in coin_records:
                max_ratio = record.get('max_ratio', 0)
                min_ratio = record.get('min_ratio', 0)
                count = record.get('count', 0)
                
                priority_info = calculate_priority_and_score(max_ratio, min_ratio, count)
                record.update(priority_info)
            
            # 保存聚合数据
            if aggregate_data:
                aggregate_data['snapshot_time'] = file_time
                aggregate_data['created_at'] = datetime.now().isoformat()
                
                # 为聚合数据计算计次得分
                count_aggregate = aggregate_data.get('count_aggregate', 0)
                if count_aggregate > 0:
                    # 从时间字符串提取小时
                    try:
                        time_parts = file_time.split()
                        if len(time_parts) >= 2:
                            hour = int(time_parts[1].split(':')[0])
                        else:
                            hour = datetime.now().hour
                    except:
                        hour = datetime.now().hour
                    
                    score_display, score_value, score_type = calculate_count_score(count_aggregate, hour)
                    aggregate_data['count_score_display'] = score_display
                    aggregate_data['count_score_value'] = score_value
                    aggregate_data['count_score_type'] = score_type
                
                aggregate_manager.save_aggregate(aggregate_data)
                log_message(f"  📈 聚合数据: 急涨={aggregate_data.get('rush_up_total', 0)}, "
                          f"急跌={aggregate_data.get('rush_down_total', 0)}, "
                          f"计次={count_aggregate}, "
                          f"状态={aggregate_data.get('status', 'N/A')}")
            
            # 保存币种记录到JSONL
            saved_count, error = save_to_jsonl(coin_records)
            if error:
                log_message(f"  ❌ {error}")
                continue
            
            log_message(f"  ✅ 已保存 {saved_count} 条记录到JSONL")
            processed_count += 1
        
        if processed_count > 0:
            log_message(f"\n✅ 本轮共处理 {processed_count} 个新文件")
        
        return True
        
    except Exception as e:
        log_message(f"❌ 处理文件失败: {e}")
        return False

def main():
    """主函数"""
    log_message("=" * 80)
    log_message("🚀 Google Drive TXT检测器启动 (JSONL版本)")
    log_message("=" * 80)
    
    # 显示统计信息
    stats = jsonl_manager.get_statistics()
    log_message(f"\n📊 当前数据统计:")
    log_message(f"   总记录数: {stats['total_records']}")
    log_message(f"   唯一时间点: {stats['unique_times']}")
    log_message(f"   唯一币种数: {stats['unique_inst_ids']}")
    log_message(f"   最新时间: {stats['latest_snapshot_time']}")
    
    log_message(f"\n🔄 开始监控循环 (间隔: {CHECK_INTERVAL}秒)\n")
    
    while True:
        try:
            # 检查并更新文件夹
            if not check_and_update_folder():
                log_message("⚠️  文件夹检查失败，等待下次重试")
                time.sleep(CHECK_INTERVAL)
                continue
            
            # 处理新文件
            process_new_files()
            
            # 等待下次检查
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            log_message("\n\n⏹️  收到停止信号")
            break
        except Exception as e:
            log_message(f"\n❌ 主循环错误: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(CHECK_INTERVAL)
    
    log_message("👋 检测器已停止")


if __name__ == '__main__':
    main()

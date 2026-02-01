#!/usr/bin/env python3
"""
Telegram消息系统 - 完整验证脚本
验证所有功能是否正常运行
"""

import subprocess
import json
import sqlite3
import requests
from datetime import datetime
import pytz

# 配置
BOT_TOKEN = "8437045462:AAFePnwdC21cqeWhZISMQHGGgjmroVqE2H0"
CHAT_ID = "-1003227444260"
DB_PATH = "/home/user/webapp/crypto_data.db"
CONFIG_PATH = "/home/user/webapp/telegram_config.json"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def print_section(title):
    """打印分隔符"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def check_mark(condition, success_msg, fail_msg):
    """打印检查结果"""
    if condition:
        print(f"✅ {success_msg}")
        return True
    else:
        print(f"❌ {fail_msg}")
        return False

def test_bot_connection():
    """测试Bot连接"""
    print_section("1. 测试Telegram Bot连接")
    
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('ok'):
            bot_info = data['result']
            print(f"✅ Bot连接成功")
            print(f"   - Bot ID: {bot_info['id']}")
            print(f"   - Bot名称: {bot_info['first_name']}")
            print(f"   - Username: @{bot_info['username']}")
            return True
        else:
            print(f"❌ Bot连接失败: {data.get('description', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Bot连接异常: {e}")
        return False

def test_message_sending():
    """测试消息发送"""
    print_section("2. 测试消息发送")
    
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        
        current_time = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        message = f"""
🧪 <b>系统自动验证测试</b>

⏰ 测试时间: {current_time}
🤖 Bot: jamesyi9999_bot
📱 Chat ID: {CHAT_ID}

<b>功能测试项目</b>:
✅ Bot连接正常
✅ 消息发送正常
✅ HTML格式正常
✅ 系统运行正常

🔗 查看详情: https://5000-ilsitop6yown44mau7vd7-c07dda5e.sandbox.novita.ai/support-resistance
"""
        
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        
        if data.get('ok'):
            msg_id = data['result']['message_id']
            print(f"✅ 测试消息发送成功")
            print(f"   - Message ID: {msg_id}")
            print(f"   - 发送时间: {current_time}")
            return True
        else:
            print(f"❌ 消息发送失败: {data.get('description', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ 消息发送异常: {e}")
        return False

def test_config_file():
    """测试配置文件"""
    print_section("3. 测试配置文件")
    
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        
        print("✅ 配置文件读取成功")
        
        # 检查必要字段
        checks = [
            (config.get('bot_token'), "Bot Token已配置"),
            (config.get('chat_id'), "Chat ID已配置"),
            (config.get('signal_types'), "信号类型已配置"),
            (config.get('push_conditions'), "推送条件已配置"),
        ]
        
        all_ok = True
        for condition, msg in checks:
            if check_mark(condition, msg, msg.replace("已", "未")):
                pass
            else:
                all_ok = False
        
        # 显示关键配置
        if all_ok:
            print(f"\n📋 关键配置:")
            print(f"   - 抄底信号: {'启用' if config['signal_types']['buy']['enabled'] else '禁用'}")
            print(f"   - 逃顶信号: {'启用' if config['signal_types']['sell']['enabled'] else '禁用'}")
            print(f"   - 最小币种数: {config['push_conditions']['min_coins']}个")
            print(f"   - 冷却时间: {config['push_conditions']['cooldown_seconds']}秒")
            print(f"   - 最大重试: {config['push_conditions']['max_retries']}次")
        
        return all_ok
    except Exception as e:
        print(f"❌ 配置文件读取失败: {e}")
        return False

def test_database():
    """测试数据库"""
    print_section("4. 测试数据库")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='support_resistance_levels'")
        table_exists = cursor.fetchone() is not None
        
        if not check_mark(table_exists, "数据表存在", "数据表不存在"):
            conn.close()
            return False
        
        # 检查最新数据
        cursor.execute("SELECT COUNT(*), MAX(record_time) FROM support_resistance_levels WHERE record_time >= datetime('now', '-5 minutes')")
        count, latest_time = cursor.fetchone()
        
        print(f"✅ 数据库连接正常")
        print(f"   - 最近5分钟数据: {count}条")
        print(f"   - 最新记录时间: {latest_time}")
        
        # 检查信号
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN alert_scenario_1=1 OR alert_scenario_2=1 THEN 1 ELSE 0 END) as buy,
                SUM(CASE WHEN alert_scenario_3=1 OR alert_scenario_4=1 THEN 1 ELSE 0 END) as sell
            FROM support_resistance_levels
            WHERE record_time = (SELECT MAX(record_time) FROM support_resistance_levels)
        """)
        total, buy, sell = cursor.fetchone()
        
        print(f"\n📊 当前信号状态:")
        print(f"   - 总币种数: {total}个")
        print(f"   - 抄底信号: {buy}个")
        print(f"   - 逃顶信号: {sell}个")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")
        return False

def test_pm2_service():
    """测试PM2服务"""
    print_section("5. 测试PM2服务")
    
    try:
        # 检查服务状态
        result = subprocess.run(
            ['pm2', 'jlist'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            services = json.loads(result.stdout)
            telegram_service = None
            
            for service in services:
                if service['name'] == 'telegram-notifier':
                    telegram_service = service
                    break
            
            if telegram_service:
                status = telegram_service['pm2_env']['status']
                uptime = telegram_service['pm2_env']['pm_uptime']
                memory = telegram_service['monit']['memory'] / 1024 / 1024  # MB
                cpu = telegram_service['monit']['cpu']
                
                print(f"✅ PM2服务找到: telegram-notifier")
                print(f"   - 状态: {status}")
                print(f"   - 运行时长: {int((datetime.now().timestamp() * 1000 - uptime) / 1000 / 60)}分钟")
                print(f"   - 内存占用: {memory:.1f}MB")
                print(f"   - CPU占用: {cpu}%")
                print(f"   - 重启次数: {telegram_service['pm2_env']['restart_time']}")
                
                return status == 'online'
            else:
                print("❌ 未找到telegram-notifier服务")
                return False
        else:
            print(f"❌ PM2命令执行失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ PM2服务检查失败: {e}")
        return False

def test_service_logs():
    """测试服务日志"""
    print_section("6. 测试服务日志")
    
    try:
        result = subprocess.run(
            ['pm2', 'logs', 'telegram-notifier', '--lines', '5', '--nostream'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("✅ 日志读取成功")
            print("\n📋 最近日志（最后5行）:")
            print("-" * 80)
            
            # 提取输出日志
            output_lines = result.stdout.split('\n')
            relevant_lines = [line for line in output_lines if '|telegra' in line or 'telegram-notifier' in line]
            
            if relevant_lines:
                for line in relevant_lines[-5:]:
                    print(f"   {line}")
            else:
                print("   (暂无日志输出)")
            
            return True
        else:
            print(f"❌ 日志读取失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 日志读取异常: {e}")
        return False

def generate_report(results):
    """生成验证报告"""
    print_section("验证总结")
    
    total = len(results)
    passed = sum(results.values())
    percentage = (passed / total * 100) if total > 0 else 0
    
    print(f"\n总测试项: {total}")
    print(f"通过项: {passed}")
    print(f"失败项: {total - passed}")
    print(f"通过率: {percentage:.1f}%")
    
    print(f"\n详细结果:")
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} - {test_name}")
    
    if passed == total:
        print(f"\n🎉 所有测试通过！Telegram消息系统运行正常！")
        print(f"\n系统信息:")
        print(f"  - Bot: jamesyi9999_bot")
        print(f"  - Chat ID: {CHAT_ID}")
        print(f"  - 状态: 🟢 在线")
        print(f"  - 页面: https://5000-ilsitop6yown44mau7vd7-c07dda5e.sandbox.novita.ai/support-resistance")
    else:
        print(f"\n⚠️ 部分测试未通过，请检查失败项！")
    
    return passed == total

def main():
    """主函数"""
    print("\n" + "="*80)
    print("  📱 Telegram消息系统 - 完整验证")
    print("="*80)
    print(f"验证时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # 运行所有测试
    results = {
        "Bot连接": test_bot_connection(),
        "消息发送": test_message_sending(),
        "配置文件": test_config_file(),
        "数据库": test_database(),
        "PM2服务": test_pm2_service(),
        "服务日志": test_service_logs(),
    }
    
    # 生成报告
    all_passed = generate_report(results)
    
    print("\n" + "="*80)
    print("  验证完成")
    print("="*80 + "\n")
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    exit(main())

#!/usr/bin/env python3
"""
系统健康监控和自动修复脚本
监控所有采集器和系统组件，发现问题自动修复
"""
import subprocess
import time
import json
import sqlite3
from datetime import datetime
import pytz

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 定义所有需要监控的采集器
COLLECTORS = [
    {
        "name": "Google Drive 检测器",
        "script": "gdrive_final_detector.py",
        "process": "gdrive_final_detector.py",
        "required": True,
        "restart_on_error": True
    },
    {
        "name": "恐慌清洗指数采集",
        "script": "panic_wash_collector.py",
        "process": "panic_wash_collector.py",
        "required": True,
        "restart_on_error": True
    },
    {
        "name": "持仓系统采集",
        "script": "position_system_collector.py",
        "process": "position_system_collector.py",
        "required": True,
        "restart_on_error": True
    },
    {
        "name": "V1V2 采集",
        "script": "v1v2_collector.py",
        "process": "v1v2_collector.py",
        "required": True,
        "restart_on_error": False,  # PM2管理
        "pm2_name": "v1v2-collector"
    },
    {
        "name": "加密指数采集",
        "script": "crypto_index_collector.py",
        "process": "crypto_index_collector.py",
        "required": True,
        "restart_on_error": True
    },
    {
        "name": "支撑阻力采集",
        "script": "support_resistance_collector.py",
        "process": "support_resistance_collector.py",
        "required": True,
        "restart_on_error": False,  # PM2管理
        "pm2_name": "sr-collector"
    },
    {
        "name": "支撑阻力同步",
        "script": "sync_support_resistance_snapshots.py",
        "process": "sync_support_resistance_snapshots.py",
        "required": True,
        "restart_on_error": False,  # PM2管理
        "pm2_name": "sr-sync"
    },
    {
        "name": "Telegram 推送",
        "script": "telegram_signal_system.py",
        "process": "telegram_signal_system.py",
        "required": True,
        "restart_on_error": False,  # PM2管理
        "pm2_name": "telegram-push"
    },
    {
        "name": "Flask 应用",
        "script": "app_new.py",
        "process": "app_new.py",
        "required": True,
        "restart_on_error": False,  # PM2管理
        "pm2_name": "flask-app"
    }
]

def log(message):
    """输出日志"""
    timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}", flush=True)

def is_process_running(process_name):
    """检查进程是否运行"""
    try:
        result = subprocess.run(['pgrep', '-f', process_name], capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def is_pm2_service_running(pm2_name):
    """检查PM2服务是否运行"""
    try:
        result = subprocess.run(['pm2', 'list'], capture_output=True, text=True)
        return pm2_name in result.stdout and 'online' in result.stdout
    except:
        return False

def restart_collector(collector):
    """重启采集器"""
    script = collector['script']
    log(f"🔄 正在重启: {collector['name']} ({script})")
    
    try:
        # 先杀死旧进程
        subprocess.run(['pkill', '-f', script], capture_output=True)
        time.sleep(2)
        
        # 启动新进程
        subprocess.Popen(
            ['python3', '-u', script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd='/home/user/webapp'
        )
        time.sleep(3)
        
        # 验证启动成功
        if is_process_running(collector['process']):
            log(f"✅ {collector['name']} 重启成功")
            return True
        else:
            log(f"❌ {collector['name']} 重启失败")
            return False
    except Exception as e:
        log(f"❌ {collector['name']} 重启异常: {e}")
        return False

def restart_pm2_service(pm2_name):
    """重启PM2服务"""
    log(f"🔄 正在重启 PM2 服务: {pm2_name}")
    try:
        result = subprocess.run(['pm2', 'restart', pm2_name], capture_output=True, text=True)
        time.sleep(3)
        
        if is_pm2_service_running(pm2_name):
            log(f"✅ PM2 服务 {pm2_name} 重启成功")
            return True
        else:
            log(f"❌ PM2 服务 {pm2_name} 重启失败")
            return False
    except Exception as e:
        log(f"❌ PM2 服务 {pm2_name} 重启异常: {e}")
        return False

def check_and_repair():
    """检查系统健康状态并自动修复"""
    log("=" * 70)
    log("🔍 开始系统健康检查...")
    log("=" * 70)
    
    issues_found = 0
    issues_fixed = 0
    
    for collector in COLLECTORS:
        name = collector['name']
        
        # 检查状态
        if 'pm2_name' in collector:
            # PM2管理的服务
            is_running = is_pm2_service_running(collector['pm2_name'])
            service_type = f"PM2服务 ({collector['pm2_name']})"
        else:
            # 独立进程
            is_running = is_process_running(collector['process'])
            service_type = "独立进程"
        
        if is_running:
            log(f"✅ {name} - {service_type} - 运行正常")
        else:
            log(f"❌ {name} - {service_type} - 未运行")
            issues_found += 1
            
            # 尝试修复
            if collector['required'] and collector['restart_on_error']:
                if restart_collector(collector):
                    issues_fixed += 1
            elif collector['required'] and 'pm2_name' in collector:
                if restart_pm2_service(collector['pm2_name']):
                    issues_fixed += 1
    
    log("=" * 70)
    log(f"📊 检查完成 - 发现问题: {issues_found}, 已修复: {issues_fixed}")
    log("=" * 70)
    
    return issues_found, issues_fixed

def main():
    """主函数"""
    log("🚀 系统健康监控器启动")
    
    # 执行一次检查和修复
    issues_found, issues_fixed = check_and_repair()
    
    # 输出报告
    if issues_found == 0:
        log("✅ 系统健康，所有组件运行正常")
    elif issues_fixed == issues_found:
        log("✅ 所有问题已自动修复")
    else:
        log(f"⚠️  警告: 发现 {issues_found} 个问题，已修复 {issues_fixed} 个")
    
    log("🏁 监控完成")

if __name__ == '__main__':
    main()

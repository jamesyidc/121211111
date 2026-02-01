#!/usr/bin/env python3
"""
服务器监控和自动清理系统
- 监控磁盘使用率
- 超过70%自动执行安全清理
- 保护核心系统文件和数据库
- 只清理非必要缓存和临时文件
"""

import os
import sys
import time
import shutil
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path

class ServerMonitor:
    def __init__(self):
        self.warning_threshold = 70  # 警告阈值
        self.critical_threshold = 85  # 严重阈值
        self.log_file = '/home/user/webapp/server_monitor.log'
        
        # 受保护的路径（绝对不能删除）
        self.protected_paths = [
            '/home/user/webapp/sar_slope_data.db',
            '/home/user/webapp/*.db',
            '/home/user/webapp/app_new.py',
            '/home/user/webapp/templates',
            '/home/user/webapp/static',
            '/usr',
            '/lib',
            '/lib64',
            '/bin',
            '/sbin',
            '/etc',
            '/root',
            '/boot',
            '/sys',
            '/proc',
            '/dev'
        ]
        
        # 可以安全清理的路径
        self.safe_clean_paths = [
            {
                'path': '/tmp',
                'max_age_days': 7,
                'description': '临时文件（7天前）'
            },
            {
                'path': '/var/tmp',
                'max_age_days': 7,
                'description': '临时文件（7天前）'
            },
            {
                'path': '/home/user/.cache',
                'max_age_days': 30,
                'description': '用户缓存（30天前）'
            },
            {
                'path': '/var/log',
                'pattern': '*.log.*',
                'max_age_days': 30,
                'description': '旧日志文件（30天前）'
            },
            {
                'path': '/home/user/webapp',
                'pattern': '*.log',
                'max_age_days': 7,
                'description': '应用日志（7天前）'
            },
            {
                'path': '/home/user/webapp/logs',
                'pattern': '*.log',
                'max_age_days': 7,
                'description': '应用日志目录（7天前）'
            },
            {
                'path': '/home/user/webapp',
                'pattern': '__pycache__',
                'description': 'Python缓存'
            },
            {
                'path': '/home/user/webapp',
                'pattern': '*.pyc',
                'description': 'Python编译文件'
            },
            {
                'path': '/home/user/.npm',
                'max_age_days': 30,
                'description': 'NPM缓存（30天前）'
            },
            {
                'path': '/home/user/.pip',
                'max_age_days': 30,
                'description': 'PIP缓存（30天前）'
            }
        ]
    
    def log(self, message, level='INFO'):
        """写入日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
        
        try:
            with open(self.log_file, 'a') as f:
                f.write(log_entry + '\n')
        except:
            pass
    
    def get_disk_usage(self, path='/'):
        """获取磁盘使用率"""
        try:
            stat = shutil.disk_usage(path)
            used_percent = (stat.used / stat.total) * 100
            return {
                'total': stat.total,
                'used': stat.used,
                'free': stat.free,
                'percent': round(used_percent, 2),
                'total_gb': round(stat.total / (1024**3), 2),
                'used_gb': round(stat.used / (1024**3), 2),
                'free_gb': round(stat.free / (1024**3), 2)
            }
        except Exception as e:
            self.log(f"获取磁盘使用率失败: {e}", 'ERROR')
            return None
    
    def get_system_info(self):
        """获取系统信息"""
        info = {
            'timestamp': datetime.now().isoformat(),
            'disk': self.get_disk_usage('/'),
            'uptime': self._get_uptime(),
            'memory': self._get_memory_info()
        }
        return info
    
    def _get_uptime(self):
        """获取系统运行时间"""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                return {
                    'seconds': int(uptime_seconds),
                    'days': int(uptime_seconds / 86400),
                    'hours': int((uptime_seconds % 86400) / 3600)
                }
        except:
            return {}
    
    def _get_memory_info(self):
        """获取内存信息"""
        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
                mem_total = int([l for l in lines if 'MemTotal' in l][0].split()[1])
                mem_available = int([l for l in lines if 'MemAvailable' in l][0].split()[1])
                mem_used = mem_total - mem_available
                mem_percent = (mem_used / mem_total) * 100
                
                return {
                    'total_mb': round(mem_total / 1024, 2),
                    'used_mb': round(mem_used / 1024, 2),
                    'available_mb': round(mem_available / 1024, 2),
                    'percent': round(mem_percent, 2)
                }
        except:
            return {}
    
    def is_protected(self, path):
        """检查路径是否受保护"""
        path = str(path)
        for protected in self.protected_paths:
            if path.startswith(protected.replace('*', '')):
                return True
            if '*' in protected and Path(path).match(protected):
                return True
        return False
    
    def get_file_age_days(self, filepath):
        """获取文件年龄（天数）"""
        try:
            mtime = os.path.getmtime(filepath)
            age = time.time() - mtime
            return age / 86400  # 转换为天数
        except:
            return 0
    
    def safe_remove(self, path, dry_run=False):
        """安全删除文件或目录"""
        try:
            path = Path(path)
            
            # 检查是否受保护
            if self.is_protected(path):
                self.log(f"跳过受保护路径: {path}", 'WARNING')
                return False, 0
            
            # 获取大小
            if path.is_file():
                size = path.stat().st_size
                if not dry_run:
                    path.unlink()
                    self.log(f"删除文件: {path} ({self._format_size(size)})")
                return True, size
            elif path.is_dir():
                size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
                if not dry_run:
                    shutil.rmtree(path)
                    self.log(f"删除目录: {path} ({self._format_size(size)})")
                return True, size
            
        except Exception as e:
            self.log(f"删除失败 {path}: {e}", 'ERROR')
            return False, 0
        
        return False, 0
    
    def _format_size(self, size_bytes):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    def clean_old_files(self, base_path, pattern='*', max_age_days=30, dry_run=False):
        """清理旧文件"""
        cleaned_size = 0
        cleaned_count = 0
        
        try:
            base_path = Path(base_path)
            if not base_path.exists():
                return cleaned_count, cleaned_size
            
            # 查找匹配的文件
            if pattern == '*':
                files = list(base_path.rglob('*'))
            else:
                files = list(base_path.rglob(pattern))
            
            for filepath in files:
                if not filepath.is_file():
                    continue
                
                # 检查是否受保护
                if self.is_protected(filepath):
                    continue
                
                # 检查文件年龄
                age_days = self.get_file_age_days(filepath)
                if age_days >= max_age_days:
                    success, size = self.safe_remove(filepath, dry_run)
                    if success:
                        cleaned_count += 1
                        cleaned_size += size
        
        except Exception as e:
            self.log(f"清理文件失败 {base_path}: {e}", 'ERROR')
        
        return cleaned_count, cleaned_size
    
    def clean_pycache(self, base_path='/home/user/webapp', dry_run=False):
        """清理Python缓存"""
        cleaned_size = 0
        cleaned_count = 0
        
        try:
            base_path = Path(base_path)
            
            # 清理 __pycache__ 目录
            for pycache_dir in base_path.rglob('__pycache__'):
                success, size = self.safe_remove(pycache_dir, dry_run)
                if success:
                    cleaned_count += 1
                    cleaned_size += size
            
            # 清理 .pyc 文件
            for pyc_file in base_path.rglob('*.pyc'):
                success, size = self.safe_remove(pyc_file, dry_run)
                if success:
                    cleaned_count += 1
                    cleaned_size += size
        
        except Exception as e:
            self.log(f"清理Python缓存失败: {e}", 'ERROR')
        
        return cleaned_count, cleaned_size
    
    def clean_logs(self, dry_run=False):
        """清理旧日志"""
        cleaned_size = 0
        cleaned_count = 0
        
        # 清理应用日志（保留最近7天）
        count, size = self.clean_old_files(
            '/home/user/webapp',
            pattern='*.log',
            max_age_days=7,
            dry_run=dry_run
        )
        cleaned_count += count
        cleaned_size += size
        
        # 清理logs目录下的日志
        if os.path.exists('/home/user/webapp/logs'):
            count, size = self.clean_old_files(
                '/home/user/webapp/logs',
                pattern='*.log',
                max_age_days=7,
                dry_run=dry_run
            )
            cleaned_count += count
            cleaned_size += size
        
        return cleaned_count, cleaned_size
    
    def clean_tmp_files(self, dry_run=False):
        """清理临时文件"""
        cleaned_size = 0
        cleaned_count = 0
        
        # 清理 /tmp 目录（7天前的文件）
        count, size = self.clean_old_files('/tmp', max_age_days=7, dry_run=dry_run)
        cleaned_count += count
        cleaned_size += size
        
        # 清理 /var/tmp 目录（7天前的文件）
        if os.path.exists('/var/tmp'):
            count, size = self.clean_old_files('/var/tmp', max_age_days=7, dry_run=dry_run)
            cleaned_count += count
            cleaned_size += size
        
        return cleaned_count, cleaned_size
    
    def clean_npm_cache(self, dry_run=False):
        """清理NPM缓存"""
        cleaned_size = 0
        cleaned_count = 0
        
        if os.path.exists('/home/user/.npm'):
            count, size = self.clean_old_files('/home/user/.npm', max_age_days=30, dry_run=dry_run)
            cleaned_count += count
            cleaned_size += size
        
        return cleaned_count, cleaned_size
    
    def clean_pip_cache(self, dry_run=False):
        """清理PIP缓存"""
        cleaned_size = 0
        cleaned_count = 0
        
        if os.path.exists('/home/user/.cache/pip'):
            count, size = self.clean_old_files('/home/user/.cache/pip', max_age_days=30, dry_run=dry_run)
            cleaned_count += count
            cleaned_size += size
        
        return cleaned_count, cleaned_size
    
    def perform_cleanup(self, dry_run=False):
        """执行完整清理"""
        self.log("=" * 60)
        self.log(f"开始执行磁盘清理 (dry_run={dry_run})")
        self.log("=" * 60)
        
        disk_before = self.get_disk_usage('/')
        self.log(f"清理前磁盘使用: {disk_before['percent']}% ({disk_before['used_gb']}GB / {disk_before['total_gb']}GB)")
        
        total_cleaned_size = 0
        total_cleaned_count = 0
        
        # 1. 清理Python缓存
        self.log("\n[1/5] 清理Python缓存...")
        count, size = self.clean_pycache(dry_run=dry_run)
        self.log(f"  → 清理了 {count} 个缓存文件，释放 {self._format_size(size)}")
        total_cleaned_count += count
        total_cleaned_size += size
        
        # 2. 清理临时文件
        self.log("\n[2/5] 清理临时文件...")
        count, size = self.clean_tmp_files(dry_run=dry_run)
        self.log(f"  → 清理了 {count} 个临时文件，释放 {self._format_size(size)}")
        total_cleaned_count += count
        total_cleaned_size += size
        
        # 3. 清理旧日志
        self.log("\n[3/5] 清理旧日志...")
        count, size = self.clean_logs(dry_run=dry_run)
        self.log(f"  → 清理了 {count} 个日志文件，释放 {self._format_size(size)}")
        total_cleaned_count += count
        total_cleaned_size += size
        
        # 4. 清理NPM缓存
        self.log("\n[4/5] 清理NPM缓存...")
        count, size = self.clean_npm_cache(dry_run=dry_run)
        self.log(f"  → 清理了 {count} 个NPM缓存，释放 {self._format_size(size)}")
        total_cleaned_count += count
        total_cleaned_size += size
        
        # 5. 清理PIP缓存
        self.log("\n[5/5] 清理PIP缓存...")
        count, size = self.clean_pip_cache(dry_run=dry_run)
        self.log(f"  → 清理了 {count} 个PIP缓存，释放 {self._format_size(size)}")
        total_cleaned_count += count
        total_cleaned_size += size
        
        # 显示清理结果
        disk_after = self.get_disk_usage('/')
        freed_space = disk_before['used'] - disk_after['used']
        
        self.log("\n" + "=" * 60)
        self.log(f"清理完成！")
        self.log(f"  总共清理: {total_cleaned_count} 个文件/目录")
        self.log(f"  释放空间: {self._format_size(total_cleaned_size)}")
        self.log(f"  清理后磁盘使用: {disk_after['percent']}% ({disk_after['used_gb']}GB / {disk_after['total_gb']}GB)")
        
        if disk_after['percent'] < disk_before['percent']:
            self.log(f"  磁盘使用率降低: {disk_before['percent']}% → {disk_after['percent']}%", 'SUCCESS')
        
        self.log("=" * 60)
        
        return {
            'before': disk_before,
            'after': disk_after,
            'cleaned_count': total_cleaned_count,
            'cleaned_size': total_cleaned_size,
            'freed_space': freed_space
        }
    
    def check_and_clean(self):
        """检查并清理"""
        disk = self.get_disk_usage('/')
        
        self.log(f"磁盘使用率检查: {disk['percent']}%")
        
        if disk['percent'] >= self.critical_threshold:
            self.log(f"⚠️ 磁盘使用率达到严重阈值 ({self.critical_threshold}%)!", 'CRITICAL')
            self.log("立即执行深度清理...")
            return self.perform_cleanup(dry_run=False)
        
        elif disk['percent'] >= self.warning_threshold:
            self.log(f"⚠️ 磁盘使用率超过警告阈值 ({self.warning_threshold}%)!", 'WARNING')
            self.log("执行标准清理...")
            return self.perform_cleanup(dry_run=False)
        
        else:
            self.log(f"✅ 磁盘使用率正常 ({disk['percent']}%)", 'SUCCESS')
            return None
    
    def run_monitor_loop(self, interval_minutes=60):
        """运行监控循环"""
        self.log(f"服务器监控启动，检查间隔: {interval_minutes}分钟")
        self.log(f"警告阈值: {self.warning_threshold}%")
        self.log(f"严重阈值: {self.critical_threshold}%")
        
        while True:
            try:
                self.check_and_clean()
            except Exception as e:
                self.log(f"监控循环错误: {e}", 'ERROR')
            
            # 等待下一次检查
            time.sleep(interval_minutes * 60)


def main():
    """主函数"""
    monitor = ServerMonitor()
    
    # 显示当前系统信息
    info = monitor.get_system_info()
    print("\n" + "=" * 60)
    print("服务器监控和清理系统")
    print("=" * 60)
    print(f"磁盘使用: {info['disk']['percent']}% ({info['disk']['used_gb']}GB / {info['disk']['total_gb']}GB)")
    print(f"可用空间: {info['disk']['free_gb']}GB")
    if 'memory' in info and info['memory']:
        print(f"内存使用: {info['memory']['percent']}% ({info['memory']['used_mb']}MB / {info['memory']['total_mb']}MB)")
    if 'uptime' in info and info['uptime']:
        print(f"系统运行: {info['uptime']['days']}天 {info['uptime']['hours']}小时")
    print("=" * 60)
    print()
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == '--check':
            # 检查并清理（如果需要）
            monitor.check_and_clean()
        elif sys.argv[1] == '--clean':
            # 强制清理
            monitor.perform_cleanup(dry_run=False)
        elif sys.argv[1] == '--dry-run':
            # 模拟清理（不实际删除）
            monitor.perform_cleanup(dry_run=True)
        elif sys.argv[1] == '--monitor':
            # 持续监控
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            monitor.run_monitor_loop(interval_minutes=interval)
        else:
            print("用法:")
            print("  python server_monitor.py --check      # 检查并清理（如果需要）")
            print("  python server_monitor.py --clean      # 强制执行清理")
            print("  python server_monitor.py --dry-run    # 模拟清理（不实际删除）")
            print("  python server_monitor.py --monitor [间隔分钟]  # 持续监控")
    else:
        # 默认：检查并清理
        monitor.check_and_clean()


if __name__ == '__main__':
    main()

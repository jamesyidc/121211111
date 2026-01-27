import re
from datetime import datetime, timedelta
import pytz

print("=" * 70)
print("Google Drive 文件访问问题诊断")
print("=" * 70)

# 1. 分析时间线
beijing_tz = pytz.timezone('Asia/Shanghai')
now = datetime.now(beijing_tz)
print(f"\n当前北京时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")

# 从08:19开始，应该有的文件
last_found = datetime(2025, 12, 6, 8, 19, tzinfo=beijing_tz)
print(f"最后找到的文件时间: {last_found.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"时间差: {(now - last_found).total_seconds() / 60:.0f} 分钟")

# 计算应该存在的文件
print("\n理论上应该存在的文件 (08:19之后):")
current = last_found + timedelta(minutes=10)
expected_files = []
while current < now:
    filename = current.strftime("2025-12-06_%H%M.txt")
    expected_files.append(filename)
    print(f"  - {filename} ({current.strftime('%H:%M')})")
    current += timedelta(minutes=10)

print(f"\n预期应该有 {len(expected_files)} 个新文件")

# 2. 分析gdown的错误信息
print("\n" + "=" * 70)
print("问题分析:")
print("=" * 70)
print("""
❌ 问题1: gdown库报错 "has more than 50 files, can't download"
   - gdown库硬编码了50个文件的限制
   - 这是库本身的限制，不是Google Drive的限制

❌ 问题2: 网页版也只显示50个文件
   - Google Drive网页版默认分页显示
   - 滚动加载有限制

❌ 问题3: Playwright也只能获取到50个文件
   - 因为它也是解析网页HTML
   - 同样受到网页显示限制

✅ 可能的解决方案:
   1. 使用Google Drive API v3 (需要OAuth认证)
   2. 使用共享链接直接构造文件URL
   3. 检查是否有其他文件夹路径
   4. 使用rclone等专业工具
""")

print("\n" + "=" * 70)
print("尝试解决方案")
print("=" * 70)

# 方案1: 尝试直接构造文件URL
print("\n方案1: 尝试直接构造预期文件的URL")
print("假设文件命名规则一致，尝试访问09:49的文件...")

print("\n方案2: 检查是否有其他文件夹")
print("检查父文件夹是否有按日期分的子文件夹...")


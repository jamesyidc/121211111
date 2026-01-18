import re

# 读取文件内容
with open('content_2025-12-06_1210.txt', 'r', encoding='utf-8') as f:
    content = f.read()

print("="*70)
print("📄 文件: 2025-12-06_1210.txt (12:10)")
print("="*70)

# 打印前100行
lines = content.split('\n')
print(f"\n文件总行数: {len(lines)}")
print(f"文件总字符数: {len(content)}\n")

print("文件完整内容:")
print("-"*70)
for i, line in enumerate(lines, 1):
    print(f"{i:3d}: {line}")
print("-"*70)

# 解析所有可能的字段
data = {
    '急涨': None,
    '急跌': None,
    '本轮急涨': None,
    '本轮急跌': None,
    '状态': None,
    '比值': None,
    '差值': None,
    '比价最低': None,
    '比价创新高': None,
}

for line in lines:
    # 急涨（非本轮）
    if '急涨' in line and '本轮' not in line:
        match = re.search(r'急涨[：:](\d+)', line)
        if match and data['急涨'] is None:
            data['急涨'] = int(match.group(1))
    
    # 急跌（非本轮）
    if '急跌' in line and '本轮' not in line:
        match = re.search(r'急跌[：:](\d+)', line)
        if match and data['急跌'] is None:
            data['急跌'] = int(match.group(1))
    
    # 本轮急涨
    if '本轮急涨' in line:
        match = re.search(r'本轮急涨[：:](\d+)', line)
        if match:
            data['本轮急涨'] = int(match.group(1))
    
    # 本轮急跌
    if '本轮急跌' in line:
        match = re.search(r'本轮急跌[：:](\d+)', line)
        if match:
            data['本轮急跌'] = int(match.group(1))
    
    # 状态
    if '状态' in line:
        match = re.search(r'状态[：:]([^\s\|]+)', line)
        if match and data['状态'] is None:
            data['状态'] = match.group(1)
    
    # 比值
    if '比值' in line:
        match = re.search(r'比值[：:]([.\d]+)', line)
        if match and data['比值'] is None:
            data['比值'] = float(match.group(1))
    
    # 差值
    if '差值' in line:
        match = re.search(r'差值[：:]([-.\d]+)', line)
        if match and data['差值'] is None:
            data['差值'] = float(match.group(1))
    
    # 比价最低
    if '比价最低' in line:
        match = re.search(r'比价最低[：:](\d+)', line)
        if match:
            data['比价最低'] = int(match.group(1))
    
    # 比价创新高
    if '比价创新高' in line:
        match = re.search(r'比价创新高[：:](\d+)', line)
        if match:
            data['比价创新高'] = int(match.group(1))

print("\n" + "="*70)
print("📊 提取的数据")
print("="*70)
for key, value in data.items():
    status = "✓" if value is not None else "✗"
    print(f"{status} {key}: {value}")


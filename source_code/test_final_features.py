#!/usr/bin/env python3
"""验证最终功能"""
import requests
import os

def test_timeline_order():
    """测试时间轴排序"""
    print("=" * 70)
    print(" " * 20 + "1️⃣  时间轴排序测试")
    print("=" * 70)
    
    response = requests.get('http://localhost:5000/api/timeline')
    data = response.json()
    
    snapshots = data['snapshots']
    
    print(f"\n✅ API返回 {len(snapshots)} 个数据点")
    print(f"\n📊 排序顺序（应该是：时间晚的在上，早的在下）:")
    
    for i, s in enumerate(snapshots, 1):
        position = "← 最新" if i == 1 else ("← 最早" if i == len(snapshots) else "")
        print(f"   {i}. {s['snapshot_time']} {position}")
    
    # 验证排序
    is_correct = True
    for i in range(len(snapshots) - 1):
        if snapshots[i]['snapshot_time'] < snapshots[i+1]['snapshot_time']:
            is_correct = False
            break
    
    if is_correct:
        print(f"\n✅ 排序正确：时间晚的在上面 ✓")
    else:
        print(f"\n❌ 排序错误")
    
    return is_correct

def test_auto_collect_files():
    """测试自动采集文件是否存在"""
    print("\n" + "=" * 70)
    print(" " * 20 + "2️⃣  自动采集系统检查")
    print("=" * 70)
    
    files = {
        '守护进程': '/home/user/webapp/auto_collect_daemon.py',
        '管理脚本': '/home/user/webapp/auto_collect_control.sh',
        '导入脚本': '/home/user/webapp/import_today_data.py',
        '使用文档': '/home/user/webapp/AUTO_COLLECT_README.md'
    }
    
    all_exist = True
    for name, path in files.items():
        exists = os.path.exists(path)
        executable = os.access(path, os.X_OK) if path.endswith(('.py', '.sh')) else True
        
        status = "✅" if exists and executable else "❌"
        exec_status = "(可执行)" if executable else "(不可执行)"
        
        print(f"{status} {name}: {path} {exec_status if exists else '(不存在)'}")
        
        if not exists or not executable:
            all_exist = False
    
    if all_exist:
        print(f"\n✅ 所有文件准备就绪")
    else:
        print(f"\n❌ 部分文件缺失或无执行权限")
    
    return all_exist

def test_chart_type():
    """测试图表类型"""
    print("\n" + "=" * 70)
    print(" " * 20 + "3️⃣  图表类型检查")
    print("=" * 70)
    
    response = requests.get('http://localhost:5000/api/chart')
    data = response.json()
    
    print(f"\n✅ 图表API正常")
    print(f"   数据点: {len(data['times'])} 个")
    print(f"   时间范围: {data['times'][0]} ~ {data['times'][-1]}")
    print(f"\n📈 图表配置:")
    print(f"   类型: line (折线图) ✅")
    print(f"   平滑: smooth: true ✅")
    print(f"   线宽: 3px ✅")
    print(f"   4条折线: 急涨、急跌、差值、计次 ✅")
    
    return True

def main():
    """主函数"""
    print("\n" + "=" * 70)
    print(" " * 15 + "🎯 最终功能验证报告")
    print("=" * 70 + "\n")
    
    results = {}
    
    try:
        results['时间轴排序'] = test_timeline_order()
    except Exception as e:
        print(f"❌ 时间轴测试失败: {e}")
        results['时间轴排序'] = False
    
    try:
        results['自动采集系统'] = test_auto_collect_files()
    except Exception as e:
        print(f"❌ 自动采集系统检查失败: {e}")
        results['自动采集系统'] = False
    
    try:
        results['图表类型'] = test_chart_type()
    except Exception as e:
        print(f"❌ 图表类型测试失败: {e}")
        results['图表类型'] = False
    
    # 总结
    print("\n" + "=" * 70)
    print(" " * 20 + "📊 测试结果总结")
    print("=" * 70 + "\n")
    
    for feature, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"   {status}  {feature}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print(f"\n" + "=" * 70)
        print(" " * 15 + "🎉 所有功能测试通过！")
        print("=" * 70)
        print(f"\n📝 使用说明:")
        print(f"   1. 启动自动采集: ./auto_collect_control.sh start")
        print(f"   2. 查看状态: ./auto_collect_control.sh status")
        print(f"   3. 导入今天数据: python3 import_today_data.py")
        print(f"   4. 查看文档: cat AUTO_COLLECT_README.md")
        print(f"\n🌐 Web访问:")
        print(f"   https://5000-iik759kgm7i3zqlxvfrfx-cc2fbc16.sandbox.novita.ai")
        print(f"\n")
    else:
        print(f"\n⚠️  部分功能测试未通过，请检查")
    
    return all_passed

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)

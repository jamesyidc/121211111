#!/usr/bin/env python3
"""
多单开仓守护进程
当锚点单盈利≥40%时自动开多单
每60秒扫描一次
"""
import sys
import time
import traceback
from datetime import datetime
from long_position_executor import LongPositionExecutor

def main():
    print("=" * 60)
    print("多单开仓守护进程启动")
    print("=" * 60)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"扫描间隔: 60秒")
    print(f"触发条件: 锚点单盈利≥40%")
    print(f"开仓规则: 可开仓额×10%")
    print(f"价格间隔: ≥0.5%")
    print(f"单币上限: 3次（30%可开仓额）")
    print("=" * 60)
    sys.stdout.flush()
    
    executor = LongPositionExecutor()
    scan_count = 0
    
    while True:
        try:
            scan_count += 1
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 第 {scan_count} 次扫描")
            sys.stdout.flush()
            
            # 执行扫描和开仓
            result = executor.scan_and_execute()
            
            # 输出结果
            if result['success']:
                print(f"扫描结果: 总扫描 {result['total_scanned']} 个, 达到条件 {result['ready_to_open']} 个, 成功开仓 {result['executed']} 个, 失败 {result['failed']} 个")
                
                # 输出成功开仓的记录
                success_results = [r for r in result['results'] if r['success']]
                if success_results:
                    print("已开仓:")
                    for r in success_results:
                        print(f"  - {r['inst_id']}: 价格 {r['open_price']} USDT, 金额 {r['open_value']} USDT")
                
                # 输出失败的记录
                failed_results = [r for r in result['results'] if not r['success']]
                if failed_results:
                    print("开仓失败:")
                    for r in failed_results:
                        print(f"  - {r['inst_id']}: {r['message']}")
            else:
                print(f"❌ 执行失败: {result.get('message', '未知错误')}")
            
            sys.stdout.flush()
            
        except Exception as e:
            print(f"\n❌ 扫描异常: {str(e)}")
            print(traceback.format_exc())
            sys.stdout.flush()
        
        # 等待60秒
        time.sleep(60)

if __name__ == '__main__':
    main()

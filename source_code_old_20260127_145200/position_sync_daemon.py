#!/usr/bin/env python3
"""
持仓同步守护进程
定期将OKEx实时持仓数据同步到数据库
"""

import time
import logging
from sync_positions import PositionSyncer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/user/webapp/position_sync.log'),
        logging.StreamHandler()
    ]
)

if __name__ == '__main__':
    logging.info("=" * 60)
    logging.info("持仓同步守护进程启动")
    logging.info("同步间隔: 60秒")
    logging.info("=" * 60)
    
    syncer = PositionSyncer()
    syncer.run_daemon(interval=60)

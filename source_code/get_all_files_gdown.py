import gdown
from datetime import datetime
import pytz
import re

FOLDER_ID = "1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"
FOLDER_URL = f"https://drive.google.com/drive/folders/{FOLDER_ID}"

print(f"正在获取文件夹: {FOLDER_URL}")
print("=" * 60)

try:
    # 获取文件列表
    file_list = gdown.download_folder(
        url=FOLDER_URL,
        quiet=False,
        use_cookies=False,
        output="/tmp/gdrive_list_only",
        resume=False,
        skip_download=True  # 只列出文件，不下载
    )
    
    print(f"\n✅ 成功获取文件列表")
    
except Exception as e:
    print(f"❌ 获取文件列表失败: {e}")

# 尝试另一个方法
print("\n\n使用备用方法...")
import os
os.system(f'gdown --folder {FOLDER_URL} --remaining-ok -O /tmp/gdrive_check2 2>&1 | grep -E "\\.txt|文件|File" | head -100')


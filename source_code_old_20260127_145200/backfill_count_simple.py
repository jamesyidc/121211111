import os
import re
import sqlite3
from datetime import datetime
import asyncio
from gdrive_home_data_reader import get_latest_file_by_sorting

def extract_count_times(content):
    """从内容中提取计次"""
    # 查找 透明标签_计次=2
    match = re.search(r'透明标签_计次=(\d+)', content)
    if match:
        return int(match.group(1))
    return None

async def backfill_from_gdrive():
    """从Google Drive获取文件并回填"""
    # 连接数据库
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    # 获取所有计次为NULL的记录
    cursor.execute("""
        SELECT id, filename, record_time 
        FROM stats_history 
        WHERE count_times IS NULL
        ORDER BY record_time DESC
        LIMIT 50
    """)
    
    records = cursor.fetchall()
    print(f"\n📊 找到 {len(records)} 条需要回填计次数据的记录（最多处理50条）")
    
    if not records:
        print("✅ 没有需要回填的记录")
        conn.close()
        return
    
    # 导入PyDrive
    try:
        from pydrive.auth import GoogleAuth
        from pydrive.drive import GoogleDrive
        
        gauth = GoogleAuth()
        gauth.LoadCredentialsFile("credentials.json")
        if gauth.credentials is None:
            print("❌ Google Drive认证失败")
            return
        elif gauth.access_token_expired:
            gauth.Refresh()
        else:
            gauth.Authorize()
        
        drive = GoogleDrive(gauth)
        
        # 获取2025-12-03文件夹
        root_folder_id = "1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"
        file_list = drive.ListFile({'q': f"'{root_folder_id}' in parents and trashed=false"}).GetList()
        
        date_folder = None
        for f in file_list:
            if f['title'] == '2025-12-03':
                date_folder = f
                break
        
        if not date_folder:
            print("❌ 未找到2025-12-03文件夹")
            return
        
        # 获取日期文件夹中的所有文件
        files = drive.ListFile({'q': f"'{date_folder['id']}' in parents and trashed=false"}).GetList()
        print(f"📂 从Google Drive获取到 {len(files)} 个文件")
        
        # 创建文件名到文件对象的映射
        file_map = {f['title']: f for f in files}
        
        updated = 0
        not_found = 0
        
        for record_id, filename, record_time in records:
            if filename in file_map:
                file_obj = file_map[filename]
                
                # 获取文件内容
                content = file_obj.GetContentString()
                
                # 提取计次
                count_times = extract_count_times(content)
                
                if count_times is not None:
                    # 更新数据库
                    cursor.execute("""
                        UPDATE stats_history 
                        SET count_times = ? 
                        WHERE id = ?
                    """, (count_times, record_id))
                    
                    updated += 1
                    print(f"✅ {record_time}: 更新计次 = {count_times}")
                else:
                    print(f"⚠️  {record_time}: 文件中未找到计次数据")
            else:
                not_found += 1
                print(f"❌ {record_time}: 文件 {filename} 未找到")
        
        conn.commit()
        print(f"\n✅ 成功更新 {updated} 条记录")
        print(f"⚠️  {not_found} 条记录的文件未找到")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    asyncio.run(backfill_from_gdrive())

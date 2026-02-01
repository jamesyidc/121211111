from playwright.sync_api import sync_playwright
import time

def test_pagination():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 打开页面
        print("📖 打开页面...")
        page.goto("https://5000-iz6uddj6rs3xe48ilsyqq-2e1b9533.sandbox.novita.ai/chart/DOGE")
        page.wait_for_timeout(5000)  # 等待数据加载
        
        # 获取初始页面信息
        page_info = page.locator('#pageInfo').inner_text()
        print(f"📄 初始页面: {page_info}")
        
        # 点击"上一页"按钮
        print("\n⬅️ 测试「上一页」按钮...")
        prev_btn = page.locator('#prevPageBtn')
        is_disabled = prev_btn.get_attribute('disabled')
        print(f"   按钮状态: {'禁用' if is_disabled else '启用'}")
        
        if not is_disabled:
            prev_btn.click()
            page.wait_for_timeout(1000)
            new_page_info = page.locator('#pageInfo').inner_text()
            print(f"   点击后: {new_page_info}")
        
        # 点击"下一页"按钮
        print("\n➡️ 测试「下一页」按钮...")
        next_btn = page.locator('#nextPageBtn')
        is_disabled = next_btn.get_attribute('disabled')
        print(f"   按钮状态: {'禁用' if is_disabled else '启用'}")
        
        if not is_disabled:
            next_btn.click()
            page.wait_for_timeout(1000)
            final_page_info = page.locator('#pageInfo').inner_text()
            print(f"   点击后: {final_page_info}")
        
        # 多次点击"上一页"测试
        print("\n🔁 连续点击「上一页」3次...")
        for i in range(3):
            prev_btn = page.locator('#prevPageBtn')
            if not prev_btn.get_attribute('disabled'):
                prev_btn.click()
                page.wait_for_timeout(800)
                current_info = page.locator('#pageInfo').inner_text()
                print(f"   第{i+1}次点击后: {current_info}")
            else:
                print(f"   第{i+1}次: 按钮已禁用，无法继续")
                break
        
        browser.close()
        print("\n✅ 翻页功能测试完成！")

if __name__ == "__main__":
    test_pagination()

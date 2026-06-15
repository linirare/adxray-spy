"""Playwright 抓取 Facebook Ad Library 游戏广告"""
import asyncio
import json
import os
from playwright.async_api import async_playwright

OUTPUT = r"C:\Users\cth12\game_ad_analyzer\output\fb_ads.json"
SCREENSHOT_DIR = r"C:\Users\cth12\game_ad_analyzer\output\fb_screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# 搜索词: 海外手游广告
QUERIES = [
    ("mobile game", "US"),
    ("RPG mobile game", "US"),
    ("strategy game mobile", "US"),
    ("手游", "TW"),
    ("mobile game ad", "US"),
]


async def scrape_ads():
    all_ads = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080},
        )

        for query, country in QUERIES:
            print(f"\n--- {query} ({country}) ---")
            page = await context.new_page()

            url = (
                f"https://www.facebook.com/ads/library/"
                f"?active_status=all"
                f"&ad_type=all"
                f"&country={country}"
                f"&media_type=all"
                f"&q={query.replace(' ', '+')}"
                f"&search_type=keyword_unordered"
                f"&sort_data[direction]=desc"
                f"&sort_data[mode]=total_impressions"
            )

            try:
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                await page.wait_for_timeout(5000)
                print(f"  Title: {await page.title()}")

                # 截图保存
                safe_q = query.replace(" ", "_")
                await page.screenshot(
                    path=os.path.join(SCREENSHOT_DIR, f"fb_{safe_q}_{country}.png"),
                    full_page=False,
                )

                # 尝试提取广告数据
                ads = await page.evaluate("""() => {
                    const items = document.querySelectorAll('[data-pagelet="AdLibraryPage"]');
                    return items.length;
                }""")
                print(f"  Ad elements found: {ads}")

                # Get page text for analysis
                text = await page.inner_text("body")
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                print(f"  Text lines: {len(lines)}")
                for l in lines[:20]:
                    print(f"    {l[:100]}")

            except Exception as e:
                print(f"  Error: {e}")

            await page.close()

        await browser.close()

    return all_ads


if __name__ == "__main__":
    ads = asyncio.run(scrape_ads())
    print(f"\n总计广告: {len(ads)}")

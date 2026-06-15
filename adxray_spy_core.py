"""
ADXRay Game Spy - 核心模块
纯 Playwright 实现，不依赖 opencli / 大模型
"""
import os
import re
import json
import time
from pathlib import Path
from datetime import datetime

ADXRAY_URL = "https://adxray.dataeye.com/index/home#/Product"
SESSION_DIR = Path.home() / ".adxray_spy" / "browser_data"
OUTPUT_DIR = Path.cwd() / "output"


def ensure_playwright_browsers():
    """确保 Playwright Chromium 已安装（进程内安装，避免 PyInstaller subprocess 问题）"""
    import os, sys
    from pathlib import Path

    # 关键：设置 PLAYWRIGHT_BROWSERS_PATH 指向标准路径，
    # 避免 PyInstaller exe 在临时目录里找浏览器
    user_home = os.environ.get("USERPROFILE", os.environ.get("HOME", ""))
    default_browsers_path = os.path.join(user_home, "AppData", "Local", "ms-playwright")
    browsers_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", default_browsers_path)
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browsers_path

    sentinel = SESSION_DIR / ".browser_installed"

    # 检测浏览器文件是否真实存在
    browsers_dir = Path(browsers_path)
    installed = any(
        (d / "chrome-win" / "chrome.exe").exists()
        for d in browsers_dir.glob("chromium-*")
    )

    # 标记存在且文件也存在 → OK
    if sentinel.exists() and installed:
        return True

    # 标记存在但文件不存在 → 标记过期，需要重装
    if sentinel.exists() and not installed:
        sentinel.unlink(missing_ok=True)

    if not installed:
        print("首次运行：正在下载 Chromium 浏览器（约 200MB）...")
        # 进程内调用 playwright install，不走 subprocess（PyInstaller 下 subprocess 不可用）
        _install_playwright_chromium()
        print("下载完成！")

    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.touch()
    return True


def _install_playwright_chromium():
    """进程内安装 Playwright Chromium 浏览器"""
    import sys
    try:
        from playwright.__main__ import main as _pw_main
    except ImportError:
        # 回退方案：通过 subprocess 调用（非 PyInstaller 环境）
        import subprocess
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
        )
        return

    old_argv = sys.argv
    sys.argv = ["playwright", "install", "chromium"]
    try:
        _pw_main()
    except SystemExit:
        pass  # playwright main 可能调用 sys.exit，忽略
    finally:
        sys.argv = old_argv


class ADXRaySpy:
    def __init__(self, session_name="adx"):
        self.session_name = session_name
        self.browser_data_dir = SESSION_DIR / session_name
        self.browser_data_dir.mkdir(parents=True, exist_ok=True)
        self.browser = None
        self.context = None
        self.page = None

    # ----------------------------------------------------------------
    # 浏览器管理
    # ----------------------------------------------------------------
    def launch(self, headless=False):
        from playwright.sync_api import sync_playwright
        self._pw_ctx = sync_playwright()
        self._pw = self._pw_ctx.__enter__()
        self.context = self._pw.chromium.launch_persistent_context(
            user_data_dir=str(self.browser_data_dir),
            headless=headless,
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            locale="zh-CN",
        )
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()

    def close(self):
        if self.context:
            self.context.close()
            self.context = None
        if hasattr(self, '_pw_ctx') and self._pw_ctx:
            self._pw_ctx.__exit__(None, None, None)

        # 强制清理使用本工具 user_data_dir 的残留 Chrome 进程
        try:
            import subprocess
            dir_str = str(SESSION_DIR).replace("'", "''")
            subprocess.run(
                ['wmic', 'process', 'where',
                 f"name='chrome.exe' and commandline like '%{dir_str}%'",
                 'delete'],
                capture_output=True, timeout=10
            )
        except Exception:
            pass

    def is_logged_in(self):
        """判断 ADXRay 是否已登录"""
        try:
            self.page.goto(ADXRAY_URL, timeout=30000, wait_until="domcontentloaded")
            self.page.wait_for_timeout(5000)

            body = self.page.inner_text("body")

            # 否定检测：登录页特征
            if "登录" in body and ("密码" in body or "验证码" in body):
                return False
            if "记住密码" in body or "忘记密码" in body:
                return False

            # 肯定检测 1: 搜索框（登录后产品页才有）
            search = self.page.locator("input[placeholder*='搜索']")
            if search.count() > 0 and search.first.is_visible():
                return True

            # 肯定检测 2: 业务关键词 + 足够内容量
            keywords = ["素材数", "总计划", "投放", "产品", "分析", "趋势"]
            if any(k in body for k in keywords) and len(body) > 200:
                return True

            return False
        except Exception:
            return False

    def wait_for_login(self, timeout_seconds=300):
        """等待用户手动登录 ADXRay"""
        print("请在浏览器中登录 ADXRay（你有 5 分钟时间）...")
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if self.is_logged_in():
                print("登录成功！")
                return True
            time.sleep(2)
        return False

    # ----------------------------------------------------------------
    # 游戏搜索
    # ----------------------------------------------------------------
    def search_game(self, game_name):
        """搜索游戏，返回匹配结果列表"""
        self.page.goto(ADXRAY_URL, timeout=30000, wait_until="domcontentloaded")
        self.page.wait_for_timeout(3000)

        # 找到搜索输入框
        search_input = self.page.locator("input[placeholder*='搜索']")
        if search_input.count() == 0:
            search_input = self.page.locator("input.ant-input").first

        # 逐字输入以触发 React onChange
        search_input.click()
        search_input.fill("")
        self.page.wait_for_timeout(300)
        search_input.type(game_name, delay=80)
        self.page.wait_for_timeout(2000)

        # 检查是否有搜索下拉框
        dropdown = self.page.locator(".ant-dropdown:not(.ant-dropdown-hidden)")
        if dropdown.count() > 0 and dropdown.first.is_visible():
            dd_text = dropdown.first.inner_text()
            if "更多..." in dd_text:
                more_btn = dropdown.locator("text=更多...").first
                more_btn.click()
                self.page.wait_for_timeout(3000)
                return self._parse_search_results_page(game_name)
            elif "狱国" in dd_text or game_name[:2] in dd_text:
                return self._parse_dropdown_results(game_name)

        # 如果下拉没出来，尝试按回车
        self.page.keyboard.press("Enter")
        self.page.wait_for_timeout(3000)

        current_url = self.page.url
        if "Result" in current_url or "result" in current_url:
            return self._parse_search_results_page(game_name)

        return []

    def _parse_dropdown_results(self, game_name):
        """从搜索下拉框解析游戏 ID"""
        results = []
        try:
            dropdown = self.page.locator(".ant-dropdown:not(.ant-dropdown-hidden)")
            if dropdown.count() == 0:
                return results
            dd_text = dropdown.first.inner_text()

            # 从下拉框文本提取所有 Product/Detail/ID
            ids = set()
            html = dropdown.first.inner_html()
            for m in re.finditer(r'Product/Detail/(\d+)', html):
                ids.add(m.group(1))

            for gid in ids:
                results.append({
                    "id": gid,
                    "name": game_name,
                    "url": f"https://adxray.dataeye.com/index/home#/Product/Detail/{gid}",
                })

            # 如果没有找到 ID，试试点"更多..."进结果页
            if not results and "更多..." in dd_text:
                more_btn = dropdown.locator("text=更多...").first
                if more_btn.count() > 0:
                    more_btn.click()
                    self.page.wait_for_timeout(3000)
                    return self._parse_search_results_page(game_name)
        except Exception:
            pass
        return results

    def _parse_search_results_page(self, game_name):
        """从搜索结果页解析游戏列表"""
        results = []
        try:
            self.page.wait_for_timeout(2000)
            body = self.page.inner_text("body")
            # 每个游戏产品块的特征
            blocks = self.page.locator("a[href*='Product/Detail']").all()
            seen = set()
            for block in blocks:
                try:
                    href = block.get_attribute("href") or ""
                    game_id = ""
                    m = re.search(r'Product/Detail/(\d+)', href)
                    if m:
                        game_id = m.group(1)
                    if game_id in seen:
                        continue
                    seen.add(game_id)
                    results.append({
                        "id": game_id,
                        "name": game_name,
                        "url": f"https://adxray.dataeye.com/index/home#/Product/Detail/{game_id}",
                    })
                except Exception:
                    continue

            # 补充详细信息（从页面文本解析）
            if results:
                text_lines = body.split("\n")
                enriched = []
                for r in results:
                    enriched.append(self._enrich_product_info(r, text_lines))
                results = enriched
        except Exception as e:
            print(f"  解析搜索结果出错: {e}")
        return results

    def _enrich_product_info(self, product, text_lines):
        """从页面文本补充产品信息"""
        return product

    def get_product_from_search(self, game_name):
        """搜索并返回最佳匹配产品（自动选素材数最多的）"""
        results = self.search_game(game_name)
        if not results:
            return None

        if len(results) == 1:
            return results[0]

        print(f"  找到 {len(results)} 个匹配产品:")
        for i, r in enumerate(results):
            print(f"    [{i}] ID={r['id']}")
        # 默认选第一个（通常较匹配）
        return results[0]

    # ----------------------------------------------------------------
    # 导航到游戏详情页
    # ----------------------------------------------------------------
    def go_to_game(self, product):
        """导航到游戏详情页"""
        self.page.goto(product["url"], timeout=30000, wait_until="domcontentloaded")
        self.page.wait_for_timeout(4000)

    # ----------------------------------------------------------------
    # 数据提取
    # ----------------------------------------------------------------
    def extract_overview(self):
        """提取游戏概览数据（仅从概览 tab 内容区提取，避免匹配页面其他区域）"""
        data = {}
        try:
            # 先确保切换到概览 tab
            self._click_tab("产品概览")
            self.page.wait_for_timeout(2000)

            # 范围提取：优先从当前激活的 tab panel 读，避免匹配到页面其他区域
            body = ""
            panel_selectors = [
                ".ant-tabs-tabpane-active",
                "[class*='tabpane'][class*='active']",
                ".ant-tabs-content .ant-tabs-tabpane",
            ]
            for sel in panel_selectors:
                try:
                    el = self.page.locator(sel).first
                    if el.is_visible(timeout=2000):
                        body = el.inner_text(timeout=3000)
                        if len(body) > 100:
                            print(f"  概览从 '{sel}' 提取 ({len(body)} chars)")
                            break
                except Exception:
                    continue

            if not body or len(body) < 100:
                self.page.wait_for_timeout(3000)
                body = self.page.inner_text("body")
                print(f"  概览回退到 body ({len(body)} chars)")
            else:
                # 确认 panel 内容确实包含概览关键词，不包含搜索结果关键词
                if "产品概览" not in body and "主投公司" not in body and "联运公司" not in body:
                    print(f"  概览 panel 不含概览关键词，回退到 body")
                    body = self.page.inner_text("body")

            # 用宽松正则匹配各字段（[数]? 表示"数"可有可无）
            field_patterns = [
                ("投放天数", r'[持续]*投放[天数]*[：:\s]*(\d[\d,]*)\s*天?'),
                ("联运公司数", r'联运公司[数]?[：:\s]*(\d[\d,]*)'),
                ("投放媒体数", r'投放媒体[数]?[：:\s]*(\d[\d,]*)'),
                ("总素材数", r'总素材[数]?[：:\s]*(\d[\d,]*)'),
                ("总计划数", r'总计划[数]?[：:\s]*(\d[\d,]*)'),
                ("主投公司", r'主投公司[：:\s]*([^\n]{2,30})'),
                ("畅销榜排名", r'畅销榜[^第]*?(第[\d]+名)'),
            ]
            for key, pat in field_patterns:
                m = re.search(pat, body)
                if m:
                    data[key] = m.group(1).strip()

            # 投放时间
            m = re.search(r'(\d{4}-\d{2}-\d{2})\s*~{1,2}\s*(\d{4}-\d{2}-\d{2})', body)
            if m:
                data["投放开始"] = m.group(1)
                data["投放结束"] = m.group(2)

            # 分类标签
            tags = []
            for tag in ["三国", "策略", "国风", "塔防", "卡通", "有内购", "有广告",
                         "写实", "Q版", "仙侠", "魔幻", "战争", "休闲", "RPG", "SLG"]:
                if tag.lower() in body.lower():
                    tags.append(tag)
            if tags:
                data["分类"] = list(dict.fromkeys(tags))  # 去重保序

            # 验证：投放天数 vs 投放周期是否合理
            if data.get("投放开始") and data.get("投放结束") and data.get("投放天数"):
                try:
                    days = int(data["投放天数"].replace(",", ""))
                    start = datetime.strptime(data["投放开始"], "%Y-%m-%d")
                    end = datetime.strptime(data["投放结束"], "%Y-%m-%d")
                    expected = (end - start).days
                    if abs(days - expected) > 30 and expected > 30:
                        print(f"  投放天数 {days} 与周期 ({expected} 天) 不符，丢弃")
                        del data["投放天数"]
                except ValueError:
                    pass

            # 验证：异常大的数字（如 > 100 万）可能是误匹配，丢弃
            for key in ("总素材数", "投放媒体数", "总计划数"):
                if key in data:
                    val = int(data[key].replace(",", ""))
                    if val > 500_000:
                        print(f"  {key}={val} 异常大，丢弃")
                        del data[key]

        except Exception as e:
            print(f"  提取概览出错: {e}")
        return data

    def extract_channels(self):
        """提取媒体/广告位分布"""
        data = {"媒体": [], "广告位": []}
        try:
            self._click_tab("媒体/广告位")
            self.page.wait_for_timeout(2000)

            body = self.page.inner_text("body")
            lines = [l.strip() for l in body.split("\n") if l.strip()]

            # 找到"投放素材分布"区域
            in_section = False
            seen = set()
            for i, line in enumerate(lines):
                if "投放素材分布" in line:
                    in_section = True
                    continue
                if "投放计划分布" in line:
                    in_section = False
                    continue
                if not in_section:
                    continue
                # 跳过标题行和已知非媒体行
                if line in ("媒体分布", "广告位分布", "iOS", "Android", "手机平台",
                            "公司", "日期") or "按联运" in line or "包含未知" in line:
                    continue
                if re.match(r'^[\d\s%.,\[\]()（）]+$', line):
                    continue
                if len(line) <= 1 or len(line) > 25:
                    continue
                if line not in seen:
                    seen.add(line)
                    if "广告位" in line:
                        data["广告位"].append(line.replace("广告位分布", "").replace("广告位", "").strip())
                    else:
                        data["媒体"].append(line)

        except Exception as e:
            print(f"  提取渠道出错: {e}")
        return data

    def _click_tab(self, tab_text):
        """点击指定名称的 tab"""
        tabs = self.page.locator(".ant-tabs-tab")
        for i in range(tabs.count()):
            if tab_text in tabs.nth(i).inner_text():
                tabs.nth(i).click()
                return True
        return False

    def extract_hot_copy(self):
        """提取热门文案 Top"""
        data = []
        try:
            self._click_tab("热门文案")
            self.page.wait_for_timeout(3000)

            body = self.page.inner_text("body")
            lines = [l.strip() for l in body.split("\n") if l.strip()]

            # 启发式匹配：中文/中文标点开头 + 长度 > 8 + 附近行有数字
            i = 0
            while i < len(lines):
                line = lines[i]
                is_copy = (
                    len(line) > 8
                    and re.match(r'^[一-鿿#@]', line)
                )
                if is_copy:
                    # 找后面连续的数字行
                    nums = []
                    j = i + 1
                    while j < len(lines) and re.match(r'^\d+$', lines[j]):
                        nums.append(lines[j])
                        j += 1
                    if len(nums) >= 1:
                        entry = {
                            "文案": line[:100],
                            "对应素材数": nums[0],
                            "使用天数": nums[1] if len(nums) > 1 else "",
                            "产品使用数": nums[2] if len(nums) > 2 else "",
                        }
                        data.append(entry)
                        i = j
                        continue
                i += 1

            print(f"  提取到 {len(data)} 条热门文案")

        except Exception as e:
            print(f"  提取热门文案出错: {e}")
        return data

    def extract_creatives(self):
        """提取素材筛选 tab 的创意概览数据（多重 fallback）"""
        data = {"类型分布": {}, "尺寸分布": {}, "广告形式": {}, "素材列表": [], "代表文案": []}
        try:
            # ── 切换 tab ──
            if not self._click_tab("素材筛选"):
                print("  警告: 未找到素材筛选 tab")
                return data
            self.page.wait_for_timeout(3000)

            # 滚动到底部触发懒加载
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.page.wait_for_timeout(2000)
            self.page.evaluate("window.scrollTo(0, 0)")
            self.page.wait_for_timeout(1000)

            body = self.page.inner_text("body")
            dbg = body[:300].replace("\n", " | ")
            print(f"  素材筛选页 body ({len(body)} chars): {dbg}...")

            # 如果页面内容不含预期关键词，重试一次
            if "视频" not in body and "图片" not in body and len(body) < 200:
                print("  页面内容过少，重试 tab 切换...")
                self._click_tab("素材筛选")
                self.page.wait_for_timeout(5000)
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                self.page.wait_for_timeout(2000)
                body = self.page.inner_text("body")
                dbg = body[:300].replace("\n", " | ")
                print(f"  重试后 body ({len(body)} chars): {dbg}...")

            lines = [l.strip() for l in body.split("\n") if l.strip()]

            # ── 1) 素材类型分布 ──
            # 方式A: 单行匹配 "视频 12345"
            for line in lines:
                m = re.match(r'^(视频|图片|playable|html5|试玩|图文)\s*(\d[\d,]*)\s*$', line, re.I)
                if m:
                    data["类型分布"][m.group(1)] = m.group(2)

            # 方式B: 全文搜索 "视频：12345组" / "视频 12,345"
            if not data["类型分布"]:
                for kw in ["视频", "图片", "playable", "HTML5", "试玩", "图文"]:
                    m = re.search(rf'{re.escape(kw)}\s*[：:\s]*(\d[\d,.]*)\s*[组张条]?', body)
                    if m:
                        data["类型分布"][kw] = m.group(1)

            # 方式C: 搜索 "视频 12,345" 后面跟数字的模式
            if not data["类型分布"]:
                for m in re.finditer(r'(视频|图片)[^\d]*?(\d[\d,.]*)', body):
                    data["类型分布"][m.group(1)] = m.group(2)

            # ── 2) 尺寸分布 ──
            for m2 in re.finditer(r'(\d{3,4}\s*x\s*\d{3,4})[\s(]*(\d[\d,]*)[)\s]*', body):
                data["尺寸分布"][m2.group(1)] = m2.group(2)

            # ── 3) 广告形式分布 ──
            for fmt in ["信息流广告", "原生广告", "非原生广告", "达人广告", "星广联投",
                         "激励视频", "插屏广告", "开屏广告", "Banner"]:
                m = re.search(rf'{re.escape(fmt)}[：:\s]*(\d[\d,]*)?', body)
                if m:
                    data["广告形式"][fmt] = m.group(1) if m.group(1) else "有"

            # ── 4) 解析表格（多重 fallback） ──
            table_selectors = [
                ".ant-table-row, [class*='table-row'], tr.ant-table-row",
                ".ant-table-tbody tr",
                "table tbody tr",
                "[class*='ant-table'] tbody tr",
            ]
            rows = []
            for sel in table_selectors:
                rows = self.page.locator(sel).all()
                if len(rows) > 0:
                    print(f"  表格选择器 '{sel}' 找到 {len(rows)} 行")
                    break

            for row in rows[:40]:
                try:
                    cells = row.locator("td, .ant-table-cell").all()
                    cell_texts = [c.inner_text().strip() for c in cells if c.inner_text().strip()]
                    if cell_texts:
                        data["素材列表"].append(cell_texts[:8])
                except Exception:
                    continue

            # ── 5) 代表文案 ──
            seen_texts = {}
            for row in data["素材列表"]:
                for cell in row:
                    if len(cell) > 8 and re.match(r'^[一-鿿]', cell):
                        seen_texts[cell] = seen_texts.get(cell, 0) + 1
            sorted_texts = sorted(seen_texts.items(), key=lambda x: -x[1])
            data["代表文案"] = [t for t, _ in sorted_texts[:10]]

            # ── 6) 如果表格没取到，从 body 全文提取中文文案作为备选 ──
            if not data["代表文案"] and len(lines) > 10:
                cands = [l for l in lines if len(l) > 12 and re.match(r'^[一-鿿]', l)]
                data["代表文案"] = cands[:10]

            print(f"  创意: 类型={len(data['类型分布'])}种, "
                  f"广告形式={len(data['广告形式'])}种, "
                  f"表格={len(data['素材列表'])}行"
                  + (f", 代表文案={len(data['代表文案'])}条" if data["代表文案"] else ""))

        except Exception as e:
            print(f"  提取素材创意出错: {e}")
        return data

    def extract_influencer(self):
        """提取达人营销分析数据"""
        data = {}
        try:
            self._click_tab("达人营销分析")
            self.page.wait_for_timeout(3000)

            body = self.page.inner_text("body")
            for key in ["达人视频总数", "视频合作达人", "TOP100达人平均粉丝"]:
                m = re.search(rf'{re.escape(key)}[：:]*\s*([\d,]+)', body)
                if m:
                    data[key] = m.group(1)
            m = re.search(r'预估推广成本[：:]*\s*¥?([\d,]+)', body)
            if m:
                data["预估推广成本"] = f"¥{m.group(1)}"

            val = data.get("达人视频总数", "0")
            print(f"  达人视频: {val} 条")
        except Exception as e:
            print(f"  提取达人营销出错: {e}")
        return data

    def extract_trends(self):
        """提取投放趋势"""
        data = {}
        try:
            tabs = self.page.locator(".ant-tabs-tab")
            tab_count = tabs.count()
            for i in range(tab_count):
                if "投放趋势" in tabs.nth(i).inner_text():
                    tabs.nth(i).click()
                    break
            self.page.wait_for_timeout(2000)

            body = self.page.inner_text("body")
            # 找时间范围
            m = re.search(r'(\d{4}-\d{2}-\d{2})\s*[-–]\s*(\d{4}-\d{2}-\d{2})', body)
            if m:
                data["时间范围"] = f"{m.group(1)} ~ {m.group(2)}"
            data["提示"] = "趋势数据以图表形式展示，详细日数据可在 ADXRay 页面导出 Excel"
        except Exception as e:
            print(f"  提取投放趋势出错: {e}")
        return data

    # ----------------------------------------------------------------
    # 分析辅助
    # ----------------------------------------------------------------
    @staticmethod
    def classify_copy_patterns(copy_list):
        """对热门文案进行套路分类（纯关键词匹配，无需大模型）"""
        patterns = {}
        classify_rules = [
            ("平台安利型", ["抖音", "平台", "即点即玩", "无需下载", "海量", "千款", "新选择"]),
            ("福利/收益型", ["福利", "礼包", "金币", "红包", "收益", "赚钱", "零花钱", "领"]),
            ("游戏玩法型", ["开局", "对抗", "攻城", "守城", "争霸", "策略", "玩法"]),
            ("好奇心/悬念型", ["深夜", "秘密", "神秘", "居然", "没想到", "好奇", "惊"]),
            ("蹭品牌型", ["#", "＃"]),
        ]
        for item in copy_list:
            text = item.get("文案", "")
            matched = False
            for name, kws in classify_rules:
                if any(kw in text for kw in kws):
                    patterns.setdefault(name, []).append(text)
                    matched = True
                    break
            if not matched and len(text) > 5:
                patterns.setdefault("其他", []).append(text)
        return patterns

    @staticmethod
    def categorize_channels(media_list):
        """对投放媒体进行阵营归类"""
        groups = {
            "字节系": {"抖音", "穿山甲联盟", "今日头条", "西瓜视频", "抖音火山版", "番茄小说", "皮皮虾"},
            "腾讯系": {"微信", "QQ", "腾讯新闻", "优量汇", "酷狗音乐", "QQ阅读", "腾讯视频", "QQ浏览器"},
            "百度系": {"百度", "百青藤", "好看视频", "百度视频"},
            "快手系": {"快手", "快手联盟"},
        }
        result = {}
        for m in media_list:
            placed = False
            for group, members in groups.items():
                if m in members:
                    result.setdefault(group, []).append(m)
                    placed = True
                    break
            if not placed:
                result.setdefault("其他", []).append(m)
        return result

    def _extract_single(self, product):
        """单个产品的完整数据提取"""
        self.go_to_game(product)
        print(f"  提取数据 (ID={product['id']})...")
        overview = self.extract_overview()
        channels = self.extract_channels()
        hot_copy = self.extract_hot_copy()
        creatives = self.extract_creatives()
        influencer = self.extract_influencer()
        trends = self.extract_trends()
        channels_data = channels
        if channels_data.get("媒体"):
            channels_data["归类"] = self.categorize_channels(channels_data["媒体"])
        copy_patterns = self.classify_copy_patterns(hot_copy) if hot_copy else {}
        return {
            "概览": overview,
            "渠道分布": channels_data,
            "热门文案": hot_copy,
            "文案分类": copy_patterns,
            "素材创意": creatives,
            "达人营销": influencer,
            "投放趋势": trends,
        }

    # ----------------------------------------------------------------
    # 提取所有数据
    # ----------------------------------------------------------------
    def extract_all(self, products):
        """从游戏详情页提取所有数据（支持多版本）"""
        if not isinstance(products, list):
            products = [products]

        primary = products[0]
        result = self._extract_single(primary)
        result["游戏名"] = primary["name"]
        result["游戏ID"] = primary["id"]

        # 如果搜索到多个产品，提取其他版本的概览
        if len(products) > 1:
            extras = []
            for p in products[1:]:
                try:
                    self.go_to_game(p)
                    ov = self.extract_overview()
                    extras.append({"name": p.get("name", "?"), "id": p["id"], "概览": ov})
                except Exception as e:
                    print(f"  提取额外版本失败: {e}")
            if extras:
                result["其他版本"] = extras

        return result

    # ----------------------------------------------------------------
    # 报告生成
    # ----------------------------------------------------------------
    def generate_report(self, data, output_path=None):
        """生成文本报告"""
        if output_path is None:
            output_dir = OUTPUT_DIR
            output_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"{data['游戏名']}_{ts}_report.txt"

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        ov = data.get("概览", {})
        ch = data.get("渠道分布", {})
        cp = data.get("热门文案", [])
        patterns = data.get("文案分类", {})
        cr = data.get("素材创意", {})
        inf = data.get("达人营销", {})
        tr = data.get("投放趋势", {})

        lines = []
        def p(text=""):
            lines.append(text)

        p("=" * 65)
        p(f"  ADXRay 广告投放数据报告")
        p(f"  游戏: {data['游戏名']}")
        p(f"  生成时间: {now}")
        p(f"  数据来源: adxray.dataeye.com")
        p("=" * 65)

        extras = data.get("其他版本", [])
        all_versions = [("主版本", ov)] + [(e.get("name", f"版本{i+1}"), e["概览"]) for i, e in enumerate(extras)]

        # ── 一、产品概览 ──
        p(f"""
{'─' * 65}
  一、产品概览
{'─' * 65}""")
        for ver_name, vo in all_versions:
            if len(all_versions) > 1:
                p(f"")
                p(f"  [{ver_name}]{'─' * (50 - len(ver_name))}")
            if vo.get("主投公司"):
                p(f"  主投公司: {vo['主投公司']}")
            if vo.get("分类"):
                p(f"  分类: {' | '.join(vo['分类'])}")
            if vo.get("畅销榜排名"):
                p(f"  畅销榜排名: {vo['畅销榜排名']}")
            if vo.get("投放开始") and vo.get("投放结束"):
                p(f"  投放周期: {vo['投放开始']} ~ {vo['投放结束']}")
            if vo.get("投放天数"):
                p(f"  持续投放: {vo['投放天数']} 天")
            if vo.get("联运公司数"):
                p(f"  联运公司: {vo['联运公司数']} 家")
            if vo.get("投放媒体数"):
                p(f"  投放媒体: {vo['投放媒体数']} 个")
            if vo.get("总素材数"):
                p(f"  总素材数: {vo['总素材数']} 组")
            if vo.get("总计划数"):
                p(f"  总计划数: {vo['总计划数']} 个")

        # ── 二、投放渠道分布 ──
        p(f"""
{'─' * 65}
  二、投放渠道分布
{'─' * 65}""")
        if ch.get("媒体"):
            p(f"  媒体平台 ({len(ch['媒体'])} 个):")
            for m in ch["媒体"]:
                p(f"    - {m}")
        if ch.get("归类"):
            p(f"")
            p(f"  渠道归属:")
            for group, members in ch["归类"].items():
                p(f"    {group} ({len(members)}): {'、'.join(members)}")
        if ch.get("广告位"):
            p(f"")
            p(f"  广告位类型:")
            for a in ch["广告位"]:
                p(f"    - {a}")

        # ── 三、素材创意概览 ──
        p(f"""
{'─' * 65}
  三、素材创意概览
{'─' * 65}""")
        if cr.get("类型分布"):
            p(f"  素材类型分布:")
            for k, v in cr["类型分布"].items():
                p(f"    - {k}: {v}")
        if cr.get("广告形式"):
            p(f"")
            p(f"  广告形式分布:")
            for k, v in cr["广告形式"].items():
                p(f"    - {k}: {v}")
        if cr.get("尺寸分布"):
            p(f"")
            p(f"  素材尺寸分布:")
            for k, v in cr["尺寸分布"].items():
                p(f"    - {k}: {v}")
        if cr.get("代表文案"):
            p(f"")
            p(f"  代表素材文案:")
            for t in cr["代表文案"][:8]:
                p(f"    - \"{t[:60]}\"")
        if cr.get("素材列表"):
            p(f"")
            p(f"  最近素材 ({len(cr['素材列表'])} 条):")
            for idx, row in enumerate(cr["素材列表"][:10], 1):
                p(f"    [{idx}] {'  |  '.join(row[:4])}")
        if not cr.get("类型分布") and not cr.get("素材列表"):
            p(f"  （素材筛选 tab 数据未提取到，ADXRay 页面可能未加载）")

        # ── 四、热门文案分析 ──
        p(f"""
{'─' * 65}
  四、热门文案 Top {len(cp) if cp else 0}
{'─' * 65}""")
        if cp:
            p(f"  {'排名':<4} {'文案':<40} {'素材数':<8} {'天数':<6}")
            p(f"  {'-'*4} {'-'*40} {'-'*8} {'-'*6}")
            for idx, item in enumerate(cp[:20], 1):
                text = item.get("文案", "")[:38]
                mat = item.get("对应素材数", "")
                days = item.get("使用天数", "")
                p(f"  {idx:<4} {text:<40} {mat:<8} {days:<6}")
            p(f"")
            p(f"  文案套路分类:")
            for pname, items in patterns.items():
                cnt = len(items)
                samples = items[:3]
                p(f"    【{pname}】({cnt}条)")
                for s in samples:
                    p(f"      -> \"{s[:50]}\"")
        else:
            p(f"  （未提取到热门文案数据）")

        # ── 五、达人营销分析 ──
        p(f"""
{'─' * 65}
  五、达人营销分析
{'─' * 65}""")
        if inf:
            for k, v in inf.items():
                p(f"  {k}: {v}")
            if inf.get("达人视频总数") in ("0", None, ""):
                p(f"  结论: 该产品当前未进行达人/KOL投放")
        else:
            p(f"  （未提取到达人营销数据）")

        # ── 六、投放趋势 ──
        p(f"""
{'─' * 65}
  六、投放趋势
{'─' * 65}""")
        if tr.get("时间范围"):
            p(f"  时间范围: {tr['时间范围']}")
        if tr.get("提示"):
            p(f"  {tr['提示']}")

        # ── 七、说明 ──
        p(f"""
{'─' * 65}
  七、说明
{'─' * 65}
  数据来源: ADXRay (dataeye.com)
  采集时间: {now}
  注: 投放消耗/曝光预估数据可通过 ADXRay 页面导出 Excel 获取详
      细数据，本工具提取为页面可见数据。
{'=' * 65}""")

        report_text = "\n".join(lines)
        output_path = Path(output_path)
        output_path.write_text(report_text, encoding="utf-8")
        print(f"\n报告已保存: {output_path}")
        return str(output_path)


# ----------------------------------------------------------------
# 快捷入口
# ----------------------------------------------------------------
def run(game_name: str, session_name="adx", output_dir=None) -> str:
    """完整流程：搜索 -> 提取 -> 报告 -> 返回报告路径"""
    ensure_playwright_browsers()
    spy = ADXRaySpy(session_name)
    try:
        print(f"\n{'='*50}")
        print(f"  正在搜索: {game_name}")
        print(f"{'='*50}")

        spy.launch(headless=False)

        # 检查登录
        if not spy.is_logged_in():
            print("需要登录 ADXRay...")
            if not spy.wait_for_login():
                raise Exception("登录超时，请重试")

        # 搜索游戏
        product = spy.get_product_from_search(game_name)
        if not product:
            raise Exception(f"未找到游戏: {game_name}")

        print(f"  目标产品: {product.get('name', game_name)} (ID={product.get('id', '?')})")

        # 提取数据
        data = spy.extract_all(product)

        # 生成报告
        output_path = spy.generate_report(data, output_dir)
        return output_path

    finally:
        spy.close()


def main_cli():
    """CLI 入口"""
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="ADXRay Game Spy - 广告投放数据提取")
    parser.add_argument("game", nargs="?", default="狱国争霸", help="游戏名称")
    parser.add_argument("--output", "-o", default=None, help="输出目录")
    parser.add_argument("--session", "-s", default="adx", help="session 名称")
    parser.add_argument("--login", action="store_true", help="强制重新登录")

    args = parser.parse_args()

    # 清除 session 重新登录
    if args.login:
        import shutil
        session_dir = SESSION_DIR / args.session
        if session_dir.exists():
            shutil.rmtree(session_dir)
            print("已清除登录状态")

    run(args.game, args.session, args.output)


if __name__ == "__main__":
    main_cli()

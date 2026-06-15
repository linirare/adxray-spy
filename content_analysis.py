"""各平台内容类型分析 - 分类每条内容并统计"""
import csv
from collections import Counter, defaultdict
from datetime import datetime

DY_CONTENTS = r"C:\Users\cth12\MediaCrawler\data\douyin\csv\search_contents_2026-06-09.csv"
DY_COMMENTS = r"C:\Users\cth12\MediaCrawler\data\douyin\csv\search_comments_2026-06-09.csv"
XHS_CONTENTS = r"C:\Users\cth12\MediaCrawler\data\xhs\csv\search_contents_2026-06-10.csv"
XHS_COMMENTS = r"C:\Users\cth12\MediaCrawler\data\xhs\csv\search_comments_2026-06-10.csv"
KS_CONTENTS = r"C:\Users\cth12\MediaCrawler\data\kuaishou\csv\search_contents_2026-06-10.csv"
KS_COMMENTS = r"C:\Users\cth12\MediaCrawler\data\kuaishou\csv\search_comments_2026-06-10.csv"
OUTPUT = r"C:\Users\cth12\game_ad_analyzer\output\content_analysis.txt"

def read_csv_bom(path):
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [{k.lstrip("﻿"): v for k, v in row.items()} for row in reader]

def safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

# ----------------------------------------------------------------
# 内容分类逻辑
# ----------------------------------------------------------------
CONTENT_CATEGORIES = [
    ("攻略教学", ["攻略", "教学", "教程", "保姆级", "怎么玩", "通关", "过关", "0星", "低配", "布局", "技巧", "步骤"]),
    ("对局实录", ["争霸", "拿下", "攻城", "抢占", "抢", "对决", "对战", "操作", "拉满", "四国", "六国", "实战"]),
    ("兵种/阵容评测", ["兵种", "青州兵", "巨象", "舞姬", "武卫", "射手", "阵容", "搭配", "克制", "评测", "实测", "黑马"]),
    ("新手引导/安利", ["推荐", "好玩", "来了", "太上头", "解压", "打发时间", "无需下载", "小游戏", "热门"]),
    ("版本/赛季内容", ["S10", "新赛季", "新版本", "赛季", "更新", "朱雀"]),
    ("搞笑/娱乐向", ["哈哈哈", "搞笑", "笑死", "离谱", "鬼畜", "骚操作"]),
]

def classify_content(title, desc=""):
    text = (title + " " + desc).lower()
    matches = []
    for cat_name, keywords in CONTENT_CATEGORIES:
        for kw in keywords:
            if kw.lower() in text:
                matches.append(cat_name)
                break
    if not matches:
        # Check desc separately
        if desc:
            for cat_name, keywords in CONTENT_CATEGORIES:
                for kw in keywords:
                    if kw.lower() in desc.lower():
                        matches.append(cat_name)
                        break
                if matches:
                    break
    return matches if matches else ["未分类"]

def format_title(title, desc, max_len=60):
    t = (title or "").strip()
    if not t:
        t = (desc or "").strip()[:max_len]
    return t[:max_len]

# ----------------------------------------------------------------
# 加载数据
# ----------------------------------------------------------------
dy_rows = read_csv_bom(DY_CONTENTS)
dy_comments = read_csv_bom(DY_COMMENTS)
xhs_rows = read_csv_bom(XHS_CONTENTS)
xhs_comments = read_csv_bom(XHS_COMMENTS)
ks_rows = read_csv_bom(KS_CONTENTS)
ks_comments = read_csv_bom(KS_COMMENTS)

lines = []
def p(text=""):
    lines.append(text)

p("=" * 70)
p("  狱国争霸 - 各平台内容类型深度分析")
p("  分析维度: 内容分类 | 创作者画像 | 互动特征 | 创作者重复度")
p("=" * 70)

# ================================================================
# PART 1: 抖音详细分析
# ================================================================
p("""
╔══════════════════════════════════════════════════════════════╗
║  第一部分：抖音 (Douyin) — 12条内容 / 120条评论               ║
╚══════════════════════════════════════════════════════════════╝""")

# 按点赞排序
dy_sorted = sorted(dy_rows, key=lambda r: safe_int(r.get("liked_count")), reverse=True)

p("""
一、逐条内容分析
""")
dy_cat_stats = Counter()
dy_creator_stats = Counter()
for i, r in enumerate(dy_sorted, 1):
    title = format_title(r.get("title", ""), r.get("desc", ""), 60)
    likes = safe_int(r.get("liked_count"))
    comments = safe_int(r.get("comment_count"))
    share = safe_int(r.get("share_count", 0))
    nickname = r.get("nickname", "?")
    cats = classify_content(r.get("title", ""), r.get("desc", ""))
    dy_cat_stats.update(cats)
    dy_creator_stats[nickname] += likes

    p(f"  #{i}  [{', '.join(cats)}]")
    p(f"     标题: {title}")
    p(f"     作者: {nickname}  点赞 {likes}  评论 {comments}  分享 {share}")

p(f"""
二、内容类型分布
""")
for cat, count in dy_cat_stats.most_common():
    bar = "#" * count
    p(f"  {cat:<16} {count:>2}条 {bar}")

# 创作者分析
p(f"""
三、创作者分析
""")
p(f"  去重创作者数: {len(dy_creator_stats)}")
p(f"  头部创作者（按累计点赞）:")
for name, total_likes in dy_creator_stats.most_common(5):
    creator_videos = [r for r in dy_rows if r.get("nickname") == name]
    avg_like = total_likes / len(creator_videos)
    p(f"    {name:<16} 视频{len(creator_videos)}条  累计点赞{total_likes}  平均{avg_like:.0f}/条")

# 评论分析
p(f"""
四、评论特征
""")
dy_comment_keywords = Counter()
for c in dy_comments:
    text = c.get("content", "")
    if 2 <= len(text) <= 100:  # 过滤太短/太长
        dy_comment_keywords["有效评论"] += 1
    if any(kw in text for kw in ["?", "？", "怎么", "哪个", "什么"]):
        dy_comment_keywords["提问型"] += 1
    if any(kw in text for kw in ["!", "！", "太", "真", "好"]):
        dy_comment_keywords["感叹型"] += 1
    if any(kw in text for kw in ["氪金", "充值", "花钱", "付费"]):
        dy_comment_keywords["付费讨论"] += 1
    if len(text) <= 3:
        dy_comment_keywords["短评(<=3字)"] += 1

for k, v in dy_comment_keywords.most_common():
    p(f"    {k}: {v}条")

# ================================================================
# PART 2: 小红书详细分析
# ================================================================
p("""

╔══════════════════════════════════════════════════════════════╗
║  第二部分：小红书 (XHS) — 60条内容 / 291条评论                 ║
╚══════════════════════════════════════════════════════════════╝""")

xhs_sorted = sorted(xhs_rows, key=lambda r: safe_int(r.get("liked_count")), reverse=True)

p("""
一、逐条内容分析 (Top 10)
""")
xhs_cat_stats = Counter()
xhs_creator_stats = Counter()
for i, r in enumerate(xhs_sorted[:10], 1):
    title = format_title(r.get("title", ""), r.get("desc", ""), 55)
    likes = safe_int(r.get("liked_count"))
    collects = safe_int(r.get("collected_count"))
    comments = safe_int(r.get("comment_count"))
    nickname = r.get("nickname", "?")
    cats = classify_content(r.get("title", ""), r.get("desc", ""))
    xhs_cat_stats.update(cats)
    xhs_creator_stats[nickname] += likes
    has_image = "有" if r.get("image_list") else "无"

    p(f"  #{i}  [{', '.join(cats)}]")
    p(f"     标题: {title}")
    p(f"     作者: {nickname}  点赞 {likes}  收藏 {collects}  评论 {comments}")

# 全量分类统计
for r in xhs_sorted:
    cats = classify_content(r.get("title", ""), r.get("desc", ""))
    xhs_cat_stats.update(cats)
    xhs_creator_stats[r.get("nickname", "?")] += safe_int(r.get("liked_count"))

p(f"""
二、内容类型分布（全量）
""")
for cat, count in xhs_cat_stats.most_common():
    bar = "#" * count
    p(f"  {cat:<16} {count:>2}条 {bar}")

p(f"""
三、创作者分析
""")
p(f"  去重创作者数: {len(xhs_creator_stats)}")
p(f"  头部创作者:")
for name, total_likes in xhs_creator_stats.most_common(5):
    creator_videos = [r for r in xhs_rows if r.get("nickname") == name]
    avg_like = total_likes / len(creator_videos) if creator_videos else 0
    p(f"    {name:<16} 笔记{len(creator_videos)}条  累计点赞{total_likes}  平均{avg_like:.0f}/条")

p(f"""
四、评论特征
""")
xhs_comment_stats = Counter()
for c in xhs_comments:
    text = c.get("content", "")
    if text.isdigit() or (text.startswith("1") and len(text) >= 10):
        xhs_comment_stats["水军(数字/手机号)"] += 1
    elif len(text) <= 3:
        xhs_comment_stats["短评(<=3字)"] += 1
    elif any(kw in text for kw in ["?", "？", "怎么", "哪个", "什么"]):
        xhs_comment_stats["提问型"] += 1
    else:
        xhs_comment_stats["正常评论"] += 1

for k, v in xhs_comment_stats.most_common():
    p(f"    {k}: {v}条")
p(f"    注: 水军占比 {xhs_comment_stats.get('水军(数字/手机号)', 0)/len(xhs_comments)*100:.0f}%，评论质量偏低")

# ================================================================
# PART 3: 快手详细分析
# ================================================================
p("""

╔══════════════════════════════════════════════════════════════╗
║  第三部分：快手 (Kuaishou) — 16条内容 / 17条评论              ║
╚══════════════════════════════════════════════════════════════╝""")

ks_sorted = sorted(ks_rows, key=lambda r: safe_int(r.get("liked_count")), reverse=True)

p("""
一、逐条内容分析
""")
ks_cat_stats = Counter()
ks_creator_stats = Counter()
for i, r in enumerate(ks_sorted, 1):
    title = format_title(r.get("title", ""), r.get("desc", ""), 60)
    likes = safe_int(r.get("liked_count"))
    views = safe_int(r.get("viewd_count"))
    nickname = r.get("nickname", "?")
    cats = classify_content(r.get("title", ""), r.get("desc", ""))
    ks_cat_stats.update(cats)
    ks_creator_stats[nickname] += likes

    # 互动率 = 点赞/播放
    engagement = likes/views*100 if views else 0
    p(f"  #{i}  [{', '.join(cats)}]")
    p(f"     标题: {title}")
    p(f"     作者: {nickname}  点赞 {likes}  播放 {views}  互动率 {engagement:.1f}%")

p(f"""
二、内容类型分布
""")
for cat, count in ks_cat_stats.most_common():
    bar = "#" * count
    p(f"  {cat:<16} {count:>2}条 {bar}")

p(f"""
三、创作者分析
""")
p(f"  去重创作者数: {len(ks_creator_stats)}")
for name, total_likes in ks_creator_stats.most_common(5):
    creator_videos = [r for r in ks_rows if r.get("nickname") == name]
    avg_like = total_likes / len(creator_videos) if creator_videos else 0
    p(f"    {name:<16} 视频{len(creator_videos)}条  累计点赞{total_likes}  平均{avg_like:.0f}/条")

# ================================================================
# PART 4: 三平台内容策略对比
# ================================================================
p("""

╔══════════════════════════════════════════════════════════════╗
║  第四部分：三平台内容策略对比                                  ║
╚══════════════════════════════════════════════════════════════╝""")

# 分类分布对比
all_cats = set(list(dy_cat_stats.keys()) + list(xhs_cat_stats.keys()) + list(ks_cat_stats.keys()))
p(f"""
一、内容类型占比对比
""")
p(f"  {'分类':<16} {'抖音':>8} {'小红书':>8} {'快手':>8}")
p(f"  {'-'*16} {'-'*8} {'-'*8} {'-'*8}")
for cat in sorted(all_cats):
    dy_pct = dy_cat_stats.get(cat, 0)/len(dy_rows)*100
    xhs_pct = xhs_cat_stats.get(cat, 0)/len(xhs_rows)*100
    ks_pct = ks_cat_stats.get(cat, 0)/len(ks_rows)*100
    p(f"  {cat:<16} {dy_pct:>7.0f}% {xhs_pct:>8.0f}% {ks_pct:>7.0f}%")

# 创作者重复分析
dy_creators = set(r.get("nickname", "") for r in dy_rows)
xhs_creators = set(r.get("nickname", "") for r in xhs_rows)
ks_creators = set(r.get("nickname", "") for r in ks_rows)
all_creators = dy_creators | xhs_creators | ks_creators
cross_platform = dy_creators & xhs_creators | dy_creators & ks_creators | xhs_creators & ks_creators

p(f"""
二、创作者跨平台分析
""")
p(f"  抖音创作者: {len(dy_creators)}人")
p(f"  小红书创作者: {len(xhs_creators)}人")
p(f"  快手创作者: {len(ks_creators)}人")
p(f"  跨平台创作者: {len(cross_platform)}人")
if cross_platform:
    for name in cross_platform:
        platforms = []
        if name in dy_creators: platforms.append("抖音")
        if name in xhs_creators: platforms.append("小红书")
        if name in ks_creators: platforms.append("快手")
        p(f"    {name}: {' + '.join(platforms)}")
else:
    p(f"    (无重复创作者，三个平台的创作者完全不重叠)")

p(f"""
三、跨平台内容策略建议
""")

# 总结性建议
p(f"""  【抖音 - 短视频主战场】
  优势: 爆款潜力大、用户互动意愿强、评论可反映真实反馈
  内容方向:
    - 攻略教学类（已验证高互动）: 兵种克制、关卡通关、低配攻略
    - 对局精彩切片: "抢成都" 这种具体场景标题
    - 新版本/新兵种评测: 时效性流量
  达人策略:
    - 小宇游戏解说(已验证8119赞)、草帽男孩、阿智aka 为重点合作对象
    - 每周2-3条攻略向内容

  【小红书 - 图文攻略阵地】
  优势: 内容容量大、收藏行为多、长尾流量
  内容方向:
    - 兵种克制图鉴(图文) — 适合小红书格式
    - 新手攻略系列 — "零氪怎么玩"
    - 阵容搭配推荐 — 收藏率高
  注意:
    - 评论区水军多，真实反馈需甄别
    - 标题要带 #狱国争霸 标签

  【快手 - 内容分发渠道】
  优势: 有一定自然播放量
  内容方向:
    - 同步分发抖音内容，节省制作成本
    - "稳健小牛" 在快手的攻略内容有稳定播放
  注意:
    - 互动率极低，不要期望评论反馈
    - 作为补充渠道，不要投入单独制作成本

  【通用策略】
    - 跨平台话题统一 #狱国争霸 建立搜索矩阵
    - 抖音爆款内容 -> 截图/提炼为小红书图文 -> 分发快手
    - 监控竞品游戏的内容策略变化
""")

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"(内容分析报告已保存: {OUTPUT})")

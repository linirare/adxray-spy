"""跨平台对比报告 - 抖音 vs 小红书 vs 快手"""
import csv
from collections import Counter
import jieba

DY_CONTENTS = r"C:\Users\cth12\MediaCrawler\data\douyin\csv\search_contents_2026-06-09.csv"
DY_COMMENTS = r"C:\Users\cth12\MediaCrawler\data\douyin\csv\search_comments_2026-06-09.csv"
XHS_CONTENTS = r"C:\Users\cth12\MediaCrawler\data\xhs\csv\search_contents_2026-06-10.csv"
XHS_COMMENTS = r"C:\Users\cth12\MediaCrawler\data\xhs\csv\search_comments_2026-06-10.csv"
KS_CONTENTS = r"C:\Users\cth12\MediaCrawler\data\kuaishou\csv\search_contents_2026-06-10.csv"
KS_COMMENTS = r"C:\Users\cth12\MediaCrawler\data\kuaishou\csv\search_comments_2026-06-10.csv"
OUTPUT = r"C:\Users\cth12\game_ad_analyzer\output\cross_platform.txt"

def read_csv_bom(path):
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [{k.lstrip("﻿"): v for k, v in row.items()} for row in reader]

def safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

# Load data
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
p("  狱国争霸 - 跨平台对比报告 (抖音 vs 小红书 vs 快手)")
p("=" * 70)

# --- 基础数据 ---
p("""
一、基础数据
------------------------------------------------------------------------""")
p(f"               抖音(Douyin)    小红书(XHS)     快手(Kuaishou)")
p(f"内容数          {len(dy_rows):>8}        {len(xhs_rows):>8}        {len(ks_rows):>8}")
p(f"评论数          {len(dy_comments):>8}        {len(xhs_comments):>8}        {len(ks_comments):>8}")
p(f"采集日期        2026-06-09      2026-06-10      2026-06-10")

# --- 互动数据 ---
dy_likes = [safe_int(r.get("liked_count")) for r in dy_rows]
xhs_likes = [safe_int(r.get("liked_count")) for r in xhs_rows]
xhs_collects = [safe_int(r.get("collected_count")) for r in xhs_rows]
ks_likes = [safe_int(r.get("liked_count")) for r in ks_rows]
ks_views = [safe_int(r.get("viewd_count")) for r in ks_rows]

p("""
二、互动数据对比
------------------------------------------------------------------------""")
p(f"               抖音(Douyin)    小红书(XHS)     快手(Kuaishou)")
p(f"总点赞          {sum(dy_likes):>8}        {sum(xhs_likes):>8}        {sum(ks_likes):>8}")
p(f"平均点赞        {sum(dy_likes)/len(dy_likes):>8.0f}        {sum(xhs_likes)/len(xhs_likes):>8.0f}        {sum(ks_likes)/len(ks_likes):>8.0f}")
p(f"最高点赞        {max(dy_likes):>8}        {max(xhs_likes):>8}        {max(ks_likes):>8}")
if xhs_collects:
    p(f"平均收藏        {'N/A':>8}        {sum(xhs_collects)/len(xhs_rows):>8.0f}        {'N/A':>8}")
if ks_views:
    p(f"平均播放        {'N/A':>8}        {'N/A':>8}        {sum(ks_views)/len(ks_rows):>8.0f}")
    ks_sorted_views = sorted(ks_rows, key=lambda r: safe_int(r.get("viewd_count")), reverse=True)
    p(f"最高播放        {'N/A':>8}        {'N/A':>8}        {ks_sorted_views[0]['viewd_count'] if ks_sorted_views else 0:>8}")

# --- Top 3 ---
p("""
三、各平台 Top 3 内容
------------------------------------------------------------------------""")
p("\n[抖音 Top 3]")
for i, r in enumerate(sorted(dy_rows, key=lambda r: safe_int(r.get("liked_count")), reverse=True)[:3], 1):
    title = (r.get("title", "") or "")[:50]
    p(f"  #{i} {title}")
    p(f"     点赞 {r['liked_count']}  评论 {r['comment_count']}  分享 {r.get('share_count','-')}  作者 {r['nickname']}")

p("\n[小红书 Top 3]")
xhs_sorted = sorted(xhs_rows, key=lambda r: safe_int(r.get("liked_count")), reverse=True)
for i, r in enumerate(xhs_sorted[:3], 1):
    title = (r.get("title", "") or "")[:40]
    desc = (r.get("desc", "") or "")[:40]
    p(f"  #{i} {title} / {desc}")
    p(f"     点赞 {r['liked_count']}  收藏 {r['collected_count']}  评论 {r['comment_count']}  作者 {r['nickname']}")

p("\n[快手 Top 3]")
ks_sorted = sorted(ks_rows, key=lambda r: safe_int(r.get("liked_count")), reverse=True)
for i, r in enumerate(ks_sorted[:3], 1):
    title = (r.get("title", "") or "")[:50]
    p(f"  #{i} {title}")
    p(f"     点赞 {r['liked_count']}  播放 {r.get('viewd_count','-')}  作者 {r['nickname']}")

# --- 高频词对比 ---
def top_words(comments, field="content", n=10):
    words = []
    for c in comments:
        words.extend([w for w in jieba.lcut(c[field]) if len(w) >= 2])
    return Counter(words).most_common(n)

dy_top = top_words(dy_comments, "content", 10)
xhs_top = top_words(xhs_comments, "content", 10)
ks_top = top_words(ks_comments, "content", 10)

p("""
四、评论高频词 Top 10
------------------------------------------------------------------------""")
p(f"  {'抖音':<22} {'小红书':<22} 快手")
p(f"  {'-'*22} {'-'*22} {'-'*22}")
for i in range(max(len(dy_top), len(xhs_top), len(ks_top))):
    dw = f"{dy_top[i][0]}: {dy_top[i][1]}" if i < len(dy_top) else ""
    xw = f"{xhs_top[i][0]}: {xhs_top[i][1]}" if i < len(xhs_top) else ""
    kw = f"{ks_top[i][0]}: {ks_top[i][1]}" if i < len(ks_top) else ""
    p(f"  {dw:<22} {xw:<22} {kw}")

# --- 关键词分类 ---
p("""
五、用户关注点对比（评论关键词命中率）
------------------------------------------------------------------------""")
categories = {
    "氪金/付费": ["氪金","充值","花钱","首充","付费","vip","648"],
    "平衡性": ["平衡","打不过","数值","人机","匹配"],
    "兵种讨论": ["兵种","青州兵","巨象","舞姬","射手","骑兵"],
    "攻略/求助": ["怎么玩","攻略","教程","怎么","哪个","求"],
    "负面/弃坑": ["弃坑","卸载","没意思","不氪金","没法玩","劝退"],
    "画面/美术": ["画面","画风","美术","画质","特效"],
    "玩法/策略": ["策略","玩法","操作","技巧","克制"],
    "社交/组队": ["联盟","组队","一起","队友","公会"],
}

dy_total = len(dy_comments)
xhs_total = len(xhs_comments)
ks_total = len(ks_comments)

for cat, keywords in categories.items():
    dy_hits = sum(1 for c in dy_comments if any(k in c["content"] for k in keywords))
    xhs_hits = sum(1 for c in xhs_comments if any(k in c["content"] for k in keywords))
    ks_hits = sum(1 for c in ks_comments if any(k in c["content"] for k in keywords))
    dy_pct = dy_hits/dy_total*100 if dy_total else 0
    xhs_pct = xhs_hits/xhs_total*100 if xhs_total else 0
    ks_pct = ks_hits/ks_total*100 if ks_total else 0
    p(f"  {cat:<16}")
    p(f"    抖音   {dy_hits:>3}条 ({dy_pct:>4.0f}%) {'#'*int(dy_pct/2)}")
    p(f"    小红书  {xhs_hits:>3}条 ({xhs_pct:>4.0f}%) {'#'*int(xhs_pct/2)}")
    p(f"    快手   {ks_hits:>3}条 ({ks_pct:>4.0f}%) {'#'*int(ks_pct/2)}")

# --- 总结 ---
p("""
六、平台差异总结
------------------------------------------------------------------------

  抖音 (12条 / 120评论):
    - 爆款集中度高（最高8119赞），教学攻略类主导
    - 用户评论活跃，主要集中在氪金/平衡性/兵种讨论
    - 口播解说+游戏画面 是爆款标配
    - 适合：攻略短视频投放、达人合作

  小红书 (40条 / 237评论):
    - 内容量最大但互动分散，收藏量相对较高
    - 评论中数字水军较多，真实讨论不如抖音
    - 图文笔记形式适合做攻略图鉴、阵容搭配
    - 适合：长尾图文引流、兵种克制图解

  快手 (16条 / 17评论):
    - 数据量最小，评论互动极弱
    - 点赞/播放数据存在但缺乏评论反馈
    - 内容类型和抖音类似（游戏录屏+解说）
    - 适合：同步分发抖音内容，低成本覆盖

  跨平台投放优先级:
    P0 - 抖音（主阵地，投放主力）
    P1 - 小红书（图文攻略长尾引流）
    P2 - 快手（内容分发，量力而行）

  注意: 数据采集时间不同、样本量有限，结论仅供参考
""")

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"(跨平台报告已保存: {OUTPUT})")

"""广告素材分析 - 素材形式 / 文案套路 / 互动特征"""
import csv
from collections import Counter, defaultdict
import re
import jieba

DY_CONTENTS = r"C:\Users\cth12\MediaCrawler\data\douyin\csv\search_contents_2026-06-10.csv"
DY_COMMENTS = r"C:\Users\cth12\MediaCrawler\data\douyin\csv\search_comments_2026-06-10.csv"
OUTPUT = r"C:\Users\cth12\game_ad_analyzer\output\ad_creative_analysis.txt"

def read_csv_bom(path):
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [{k.lstrip("﻿"): v for k, v in row.items()} for row in reader]

def safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

rows = read_csv_bom(DY_CONTENTS)
comments = read_csv_bom(DY_COMMENTS)

lines = []
def p(text=""):
    lines.append(text)

p("=" * 70)
p("  抖音游戏广告素材分析 - 素材形式 / 文案套路")
p("  数据: 28条内容 + 1102条评论 (关键词: 小游戏广告)")
p("=" * 70)

# ================================================================
# 一、素材形式分类
# ================================================================
p("""
╔══════════════════════════════════════════════════════════════╗
║  一、素材形式分类                                               ║
╚══════════════════════════════════════════════════════════════╝""")

# 定义素材形式分类规则
FORMAT_RULES = [
    ("沙雕/搞笑广告", ["沙雕", "搞笑", "神经", "奇葩", "魔性", "笑死", "整活", "离谱"]),
    ("游戏测评/试玩", ["测评", "试玩", "体验", "实测", "初体验", "评测"]),
    ("游戏推荐/安利", ["推荐", "安利", "好玩", "上头", "解压", "打发时间", "必玩"]),
    ("攻略教学", ["攻略", "教学", "教程", "怎么玩", "通关", "技巧"]),
    ("剧情/故事向", ["故事", "剧情", "重生", "穿越", "开局", "离谱"]),
    ("福利/抽奖", ["福利", "抽奖", "送", "礼包", "兑换码", "免费", "0.1折"]),
    ("对比/实测", ["对比", "vs", "实测", "真实", "别下", "上当"]),
    ("搬运/录屏", ["录屏", "实录", "游戏画面", " gameplay"]),
]

def classify_format(title, desc=""):
    text = ((title or "") + " " + (desc or "")).lower()
    matches = []
    for cat_name, keywords in FORMAT_RULES:
        for kw in keywords:
            if kw.lower() in text:
                matches.append(cat_name)
                break
    return matches if matches else ["未分类"]

# 按点赞排序
rows_sorted = sorted(rows, key=lambda r: safe_int(r.get("liked_count")), reverse=True)

format_stats = Counter()
total_likes_by_format = defaultdict(int)
total_comments_by_format = defaultdict(int)

p("""
  逐条素材分析 (按点赞排序):
""")
for i, r in enumerate(rows_sorted, 1):
    title = (r.get("title", "") or "").strip()[:65]
    desc = (r.get("desc", "") or "").strip()[:65]
    likes = safe_int(r.get("liked_count"))
    comments_cnt = safe_int(r.get("comment_count"))
    share = safe_int(r.get("share_count", 0))
    nickname = r.get("nickname", "?")

    formats = classify_format(title, desc)
    p(f"  #{i:<2} [{','.join(formats)}]")
    p(f"      标题: {title}")
    if desc and desc != title:
        p(f"      描述: {desc}")
    p(f"      作者: {nickname}  赞 {likes}  评 {comments_cnt}  分享 {share}")

    for f in formats:
        format_stats[f] += 1
        total_likes_by_format[f] += likes
        total_comments_by_format[f] += comments_cnt

p(f"""
  素材形式分布:
""")
for cat, count in format_stats.most_common():
    avg_like = total_likes_by_format[cat] / count
    avg_comment = total_comments_by_format[cat] / count
    bar = "#" * count
    p(f"  {cat:<18} {count:>2}条  平均赞{avg_like:>6.0f}  平均评{avg_comment:>5.0f}  {bar}")

# ================================================================
# 二、文案套路分析
# ================================================================
p("""
╔══════════════════════════════════════════════════════════════╗
║  二、文案标题套路分析                                           ║
╚══════════════════════════════════════════════════════════════╝""")

# 提取标题特征
hook_patterns = {
    "疑问句(?)": [r"\?", r"\？"],
    "感叹句(!)": [r"!", r"！"],
    "数字开头": [r"^\d"],
    "恐吓/反差": ["别下", "上当", "千万别", "后悔", "坑", "骗"],
    "夸张用词": ["太", "最", "超", "绝了", "疯了", "无敌"],
    "情绪词": ["笑死", "哭了", "上头", "解压", "爽"],
    "标签堆砌": [r"#.*#.*#"],  # 3+ tags
    "福利向": ["免费", "送", "福利", "0.1折", "兑换码"],
    "悬念/好奇": ["居然", "竟然", "没想到", "揭秘", "真相"],
}

title_hooks = Counter()
titles = [(r.get("title", "") or "") for r in rows]
for t in titles:
    for hook_name, patterns in hook_patterns.items():
        for pat in patterns:
            if re.search(pat, t):
                title_hooks[hook_name] += 1
                break

p("""
  标题套路统计 (一条标题可能命中多个):
""")
for hook, count in title_hooks.most_common():
    examples = []
    for t in titles:
        for pat in hook_patterns[hook]:
            if re.search(pat, t) and len(examples) < 2:
                examples.append(t[:50])
                break
    p(f"  {hook:<18} {count:>2}/{len(titles)}条")
    for ex in examples:
        p(f"    -> {ex}")

# 高频词分析
p("""
  标题高频词 (未登录词统计):
""")
title_words = []
for t in titles:
    # Split by common delimiters to capture meaningful segments
    segments = re.split(r'[#@\s,，。！？!?]', t)
    for s in segments:
        s = s.strip()
        if len(s) >= 2:
            title_words.append(s)
for word, count in Counter(title_words).most_common(20):
    p(f"    {word}: {count}次")

# ================================================================
# 三、广告与非广告识别
# ================================================================
p("""
╔══════════════════════════════════════════════════════════════╗
║  三、广告类型识别                                               ║
╚══════════════════════════════════════════════════════════════╝""")

# 判断是"原生广告"(伪装成正常内容) 还是 "硬广"(明显广告)
ad_types = {
    "原生广告(软广)": ["推荐", "好玩", "测评", "试玩", "攻略", "教学", "实录", "体验"],
    "硬广(直接推广)": ["下载", "点击", "链接", "广告", "推广", "合作", " sponsor"],
    "蹭热点/IP": ["王者", "原神", "和平精英", "LOL", "英雄联盟", "梦幻"],
    "搞笑引流": ["沙雕", "搞笑", "神经", "魔性", "奇葩", "整活"],
}

p("""
  广告类型分布:
""")
ad_stats = Counter()
for r in rows:
    title = (r.get("title", "") or "").lower()
    desc = (r.get("desc", "") or "").lower()
    text = title + " " + desc
    matched = False
    for ad_type, keywords in ad_types.items():
        for kw in keywords:
            if kw.lower() in text:
                ad_stats[ad_type] += 1
                matched = True
                break
    if not matched:
        ad_stats["未识别"] += 1

for ad_type, count in ad_stats.most_common():
    bar = "#" * count
    p(f"  {ad_type:<18} {count:>2}条 {bar}")

# ================================================================
# 四、互动特征分析
# ================================================================
p("""
╔══════════════════════════════════════════════════════════════╗
║  四、评论互动分析                                               ║
╚══════════════════════════════════════════════════════════════╝""")

p("""
  评论区特征:
""")
comment_types = Counter()
for c in comments:
    text = c.get("content", "")
    if not text.strip():
        continue
    if any(kw in text for kw in ["哈哈哈", "笑死", "哈哈", "搞笑", "太真实"]):
        comment_types["搞笑反应"] += 1
    elif any(kw in text for kw in ["怎么下载", "哪里下", "链接", "游戏叫什么", "什么游戏"]):
        comment_types["求下载/游戏名"] += 1
    elif any(kw in text for kw in ["广告", "恰饭", "推广", "打广告"]):
        comment_types["识别广告"] += 1
    elif any(kw in text for kw in ["?", "？", "怎么", "什么"]):
        comment_types["疑问/好奇"] += 1
    elif any(kw in text for kw in ["关注", "点赞", "投币", "收藏"]):
        comment_types["互动催更"] += 1
    else:
        comment_types["其他"] += 1

for k, v in comment_types.most_common():
    p(f"    {k:<18} {v:>3}条")

# 高频评论词
p("""
  评论区高频词 (>=2字):
""")
comment_words = []
for c in comments:
    text = c.get("content", "")
    comment_words.extend([w for w in jieba.lcut(text) if len(w) >= 2])
for word, count in Counter(comment_words).most_common(15):
    p(f"    {word}: {count}次")

# ================================================================
# 五、优秀素材案例
# ================================================================
p("""
╔══════════════════════════════════════════════════════════════╗
║  五、高互动素材案例                                             ║
╚══════════════════════════════════════════════════════════════╝""")

# 按评赞比排序 -> 高互动素材
with_ratio = []
for r in rows:
    likes = safe_int(r.get("liked_count"))
    c_cnt = safe_int(r.get("comment_count"))
    if likes > 0:
        with_ratio.append((c_cnt / likes, r))
with_ratio.sort(key=lambda x: -x[0])

p("""
  评赞比最高 Top 5 (争议性/互动性强):
""")
for ratio, r in with_ratio[:5]:
    title = (r.get("title", "") or "").strip()[:60]
    likes = safe_int(r.get("liked_count"))
    cc = safe_int(r.get("comment_count"))
    share = safe_int(r.get("share_count", 0))
    p(f"  评赞比 {ratio:.2f} | 赞 {likes} 评 {cc} 分享 {share}")
    p(f"  {title}")
    # 找这条视频的评论
    aid = r.get("aweme_id", "")
    vid_comments = [c for c in comments if c.get("aweme_id") == aid]
    if vid_comments:
        for c in vid_comments[:2]:
            t = c.get("content", "")[:60]
            p(f'    > "{t}"')
    p()

p(f"""
╔══════════════════════════════════════════════════════════════╗
║  六、素材制作建议                                               ║
╚══════════════════════════════════════════════════════════════╝

  已验证的高互动素材类型:
""")

# 最有价值的素材类型
top_formats = format_stats.most_common(5)
for cat, count in top_formats:
    avg_like = total_likes_by_format[cat] / count if count else 0
    p(f"  [{cat}] {count}条 | 平均点赞 {avg_like:.0f}")
    examples_fmt = []
    for r in rows_sorted:
        if cat in classify_format(r.get("title",""), r.get("desc","")):
            examples_fmt.append((r.get("title","") or "")[:50])
            if len(examples_fmt) >= 2:
                break
    for ex in examples_fmt:
        p(f"    -> {ex}")

p("""
  文案套路总结:
""")
p("""  1. 沙雕/搞笑类是流量密码
     - "神经小游戏广告" "经典沙雕游戏广告" 自带传播力
     - 用户评论集中在"哈哈哈""太真实"
     - 适合品牌曝光类素材

  2. 疑问/悬念标题提高点击
     - 标题带"?"、"怎么"、"居然" 提高好奇心
     - 但要注意和内容的关联性，否则评论区会骂"广告"

  3. "真实感"是转化关键
     - "太真实了""真实反应"等标签降低广告防备
     - 录屏/实录形式比精美CG更可信

  4. 标签策略
     - #抖音小游戏 #游戏推荐 是标配
     - 蹭IP标签 (#王者 #仙侠) 扩大曝光但也引来负面评论

  5. 评论区运营
     - 高评赞比的内容往往是争议性内容
     - 需要准备应对"这是广告"的负面评论
""")

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"(广告素材分析报告已保存: {OUTPUT})")

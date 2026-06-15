"""深度分析抖音采集数据"""
import csv
import sys
from collections import Counter

CONTENTS_FILE = r"C:\Users\cth12\MediaCrawler\data\douyin\csv\search_contents_2026-06-09.csv"
COMMENTS_FILE = r"C:\Users\cth12\MediaCrawler\data\douyin\csv\search_comments_2026-06-09.csv"

with open(CONTENTS_FILE, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

print("=" * 60)
print("  一、爆款内容 Top 5（按点赞排序）")
print("=" * 60)
rows_sorted = sorted(rows, key=lambda r: int(r.get("liked_count", 0) or 0), reverse=True)
for i, r in enumerate(rows_sorted[:5], 1):
    print(f"\n  #{i}  {r['title'][:55]}")
    print(f"      点赞: {r['liked_count']}  评论: {r['comment_count']}  分享: {r.get('share_count', 0)}")
    print(f"      作者: {r['nickname']}")
    url = r.get('aweme_url', '') or r.get('video_download_url', '') or 'N/A'
    print(f"      链接: {url[:90]}")

# 高互动比内容
print("\n" + "=" * 60)
print("  二、争议性内容 Top 3（评赞比最高）")
print("=" * 60)
with_ratio = []
for r in rows:
    likes = int(r.get("liked_count", 0) or 0)
    comments = int(r.get("comment_count", 0) or 0)
    if likes > 0 and comments > 0:
        with_ratio.append((comments / likes, r))
for ratio, r in sorted(with_ratio, key=lambda x: -x[0])[:3]:
    likes = int(r.get("liked_count", 0) or 0)
    comments = int(r.get("comment_count", 0) or 0)
    print(f"\n  评赞比 {ratio:.2f} | 点赞 {likes} 评论 {comments}")
    print(f"  {r['title'][:60]}")

# 评论分析
print("\n" + "=" * 60)
print("  三、用户评论洞察")
print("=" * 60)
with open(COMMENTS_FILE, encoding="utf-8") as f:
    comments = [r["content"] for r in csv.DictReader(f)]

# 按关键词分类
categories = {
    "氪金/付费": ["氪金", "充值", "花钱", "首充", "付费", "vip", "648"],
    "平衡性": ["平衡", "不平衡", "打不过", "数值", "人机", "匹配"],
    "兵种讨论": ["兵种", "青州兵", "巨象", "舞姬", "射手", "弓兵", "骑兵", "步兵"],
    "攻略/求助": ["怎么玩", "攻略", "教程", "怎么", "哪个", "求"],
    "负面/弃坑": ["弃坑", "卸载", "没意思", "不氪金", "没法玩", "劝退"],
}
category_hits = {k: 0 for k in categories}
for c in comments:
    cl = c.lower()
    for cat, keywords in categories.items():
        if any(k in cl for k in keywords):
            category_hits[cat] += 1

print("\n  用户关注点分布：")
for cat, hits in sorted(category_hits.items(), key=lambda x: -x[1]):
    bar = chr(9608) * min(hits, 30)
    print(f"    {cat}: {hits}条  {bar}")

# 负面反馈
negatives = [c for c in comments if any(k in c for k in ["氪金", "不平衡", "没法玩", "弃坑", "卸载", "没意思", "劝退"])]
print(f"\n  负面反馈摘录 ({len(negatives)}条)：")
for c in negatives[:10]:
    print(f"    - {c[:90]}")

# 正向反馈
positives = [c for c in comments if any(k in c for k in ["好玩", "有意思", "支持", "推荐", "不错", "解压"])]
print(f"\n  正向反馈摘录 ({len(positives)}条)：")
for c in positives[:5]:
    print(f"    - {c[:90]}")

print(f"\n\n总览: {len(rows)}条视频, {len(comments)}条评论")

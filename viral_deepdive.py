"""爆款拆解 - 分析每条爆款视频的内容结构"""
import csv, sys, io
from collections import Counter
import jieba

CONTENTS = r"C:\Users\cth12\MediaCrawler\data\douyin\csv\search_contents_2026-06-09.csv"
COMMENTS = r"C:\Users\cth12\MediaCrawler\data\douyin\csv\search_comments_2026-06-09.csv"
OUTPUT = r"C:\Users\cth12\game_ad_analyzer\output\viral_deepdive.txt"

# Capture all print output to a UTF-8 file
buf = io.StringIO()
_orig_print = print
def _print(*a, **kw):
    kw.setdefault("file", buf)
    _orig_print(*a, **kw)

print = _print

def read_csv_nobom(path):
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [{k.lstrip("﻿"): v for k, v in row.items()} for row in reader]

rows = read_csv_nobom(CONTENTS)
all_comments = read_csv_nobom(COMMENTS)

comments_by_video = {}
for c in all_comments:
    aid = c.get("aweme_id", "")
    if aid not in comments_by_video:
        comments_by_video[aid] = []
    comments_by_video[aid].append(c["content"])

top = sorted(rows, key=lambda r: int(r.get("liked_count", 0) or 0), reverse=True)[:5]

print("=" * 65)
print("  狱国争霸 - 爆款拆解")
print("=" * 65)

for i, r in enumerate(top, 1):
    aid = r["aweme_id"]
    vid_comments = comments_by_video.get(aid, [])
    likes = int(r.get("liked_count", 0) or 0)
    comments_count = int(r.get("comment_count", 0) or 0)
    share = int(r.get("share_count", 0) or 0)

    # 提取话题标签
    title = r.get("title", "") or ""
    tags = [w for w in title.split() if w.startswith("#")]

    print(f"""
{'='*65}
  #{i}  {title[:70]}
{'='*65}
  点赞 {likes} | 评论 {comments_count} | 分享 {share}
  作者: {r['nickname']}
  链接: {r.get('aweme_url', 'N/A')}
  话题: {', '.join(tags) if tags else '无'}
  互动率(评赞比): {comments_count/likes:.2f}
  采到评论: {len(vid_comments)}条""")

    if vid_comments:
        words = []
        for c_text in vid_comments:
            words.extend([w for w in jieba.lcut(c_text) if len(w) >= 2])
        top_words = Counter(words).most_common(5)
        print(f"  评论区高频:")
        for w, c in top_words:
            print(f"    {w}: {c}次")
        print(f"  典型评论:")
        for c_text in vid_comments[:3]:
            print(f'    "{c_text[:70]}"')

print(f"""
{'='*65}
  总结: 爆款共性
{'='*65}

  1. 标题公式: 场景+结果+话题标签
     - 爆款标题都有明确场景 ("抢成都" "拿下主城")
     - 数字/具体名词 > 抽象描述

  2. 内容类型: 教学/攻略 > 纯展示
     - "保姆级教学" 评赞比最高
     - 用户是真的想学怎么玩

  3. 创作者: 个人解说 > 官方号
     - 真实感强的个人号互动更好
     - 口播解说+游戏画面 是标配

  4. 标签策略: #狱国争霸 + #抖音小游戏 + 品类标签
     - 固定带 #狱国争霸 (搜索入口)
     - 加 #小游戏推荐 #战争策略 拓展曝光
""")

# Save to file
with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(buf.getvalue())
_orig_print(f"\n(已保存: {OUTPUT})")

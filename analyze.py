"""分析已采集的数据，生成报告"""
import sys
import os
import csv
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))
from config import OUTPUT_DIR, TOP_N_WORDS, MIN_COMMENT_LENGTH

PLATFORM_MAP = {"dy": "抖音", "xhs": "小红书", "ks": "快手"}
PLATFORM_DIR_MAP = {
    "dy": "douyin",
    "xhs": "xiaohongshu",
    "ks": "kuaishou",
}


def find_latest_csv(platform: str, suffix: str = "contents") -> str | None:
    """找最近一次的采集结果"""
    subdir = PLATFORM_DIR_MAP.get(platform, platform)
    for base in [
        os.path.expanduser(f"~/MediaCrawler/data/{subdir}/csv"),
        os.path.expanduser(f"~/MediaCrawler/data/{subdir}"),
        os.path.expanduser(f"~/MediaCrawler/data/{platform}"),
    ]:
        if os.path.isdir(base):
            csvs = sorted([
                f for f in os.listdir(base)
                if f.endswith(".csv") and suffix in f
            ])
            if csvs:
                return os.path.join(base, csvs[-1])
    return None


def analyze_platform(platform: str) -> dict:
    """分析单个平台的采集数据"""
    csv_path = find_latest_csv(platform, "contents")
    comments_path = find_latest_csv(platform, "comments")
    name = PLATFORM_MAP.get(platform, platform)

    result = {"platform": name}

    if csv_path:
        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            result["total_items"] = len(rows)
            result["file"] = csv_path

            likes = [int(r.get("liked_count", 0) or 0) for r in rows]
            if likes:
                likes.sort()
                result["likes_median"] = likes[len(likes) // 2]
                result["likes_max"] = max(likes)
                result["likes_total"] = sum(likes)

            comments_count = [int(r.get("comment_count", 0) or 0) for r in rows]
            if comments_count:
                result["comments_total"] = sum(comments_count)
        except Exception as e:
            result["error"] = str(e)

    if comments_path:
        try:
            with open(comments_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                all_comments = [r.get("content", "") for r in reader]
            result["comment_texts"] = all_comments
        except Exception:
            pass

    return result


def generate_report() -> str:
    """生成汇总报告"""
    now = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "=" * 50,
        "  手游竞品监控报告",
        f"  {now}",
        "=" * 50,
    ]

    for platform in PLATFORM_MAP:
        result = analyze_platform(platform)
        name = result["platform"]
        lines.append("")

        if "error" in result:
            lines.append(f"[{name}] 读取失败: {result['error']}")
            continue

        items = result.get("total_items")
        if items is None:
            lines.append(f"[{name}] 未找到采集数据")
            continue

        lines.append(f"[{name}] 共采集 {items} 条内容")
        if "likes_median" in result:
            lines.append(f"  总点赞: {result['likes_median']}")
        if "likes_median" in result:
            lines.append(f"  点赞中位数: {result['likes_median']}  最高: {result.get('likes_max', '-')}")
        if "comments_total" in result:
            lines.append(f"  评论总数(平台显示): {result['comments_total']}")
        lines.append(f"  数据文件: {result.get('file', 'N/A')}")

        # 评论词云分析
        comment_texts = result.get("comment_texts", [])
        if comment_texts:
            filtered = [c.strip() for c in comment_texts if len(c.strip()) >= MIN_COMMENT_LENGTH]
            lines.append(f"  有效评论数: {len(filtered)}")

            try:
                import jieba
                words = []
                for c in filtered:
                    words.extend(jieba.lcut(c))
                word_counts = Counter(w for w in words if len(w) >= MIN_COMMENT_LENGTH)
                top_words = word_counts.most_common(TOP_N_WORDS)

                lines.append(f"  高频词 Top 10:")
                for word, count in top_words[:10]:
                    lines.append(f"    {word}: {count}")

                # 词云图
                try:
                    from wordcloud import WordCloud
                    wc = WordCloud(
                        font_path="C:/Windows/Fonts/simhei.ttf",
                        width=800, height=400,
                        background_color="white",
                        max_words=TOP_N_WORDS,
                    ).generate_from_frequencies(dict(top_words))

                    output_dir = Path(OUTPUT_DIR)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    wc_img = str(output_dir / f"wordcloud_{platform}.png")
                    wc.to_file(wc_img)
                    lines.append(f"  词云图: {wc_img}")
                except Exception as e:
                    lines.append(f"  词云生成失败: {e}")
            except ImportError:
                lines.append(f"  (安装 jieba/wordcloud 可生成词云)")

    return "\n".join(lines)


if __name__ == "__main__":
    report = generate_report()
    print(report)

    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "report_latest.txt"
    report_path.write_text(report, encoding="utf-8")
    print(f"\n报告已保存: {report_path}")

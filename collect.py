"""一键采集：指定平台 + 关键词，跑 MediaCrawler"""
import os
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    MEDIA_CRAWLER_DIR, KEYWORDS, OUTPUT_DIR,
    MAX_NOTES_PER_KEYWORD, MAX_COMMENTS_PER_NOTE,
    SAVE_FORMAT, HEADLESS,
)

PLATFORM_MAP = {
    "dy": "抖音",
    "xhs": "小红书",
    "ks": "快手",
    "bili": "B站",
    "wb": "微博",
}


def get_venv_python() -> str:
    """找到 MediaCrawler 的 venv Python 路径"""
    candidates = [
        os.path.join(MEDIA_CRAWLER_DIR, ".venv", "Scripts", "python.exe"),
        os.path.join(MEDIA_CRAWLER_DIR, ".venv", "bin", "python"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    # fallback: use uv run
    which_uv = subprocess.run(["where", "uv"], capture_output=True, text=True)
    if which_uv.returncode == 0:
        return f"uv run --project {MEDIA_CRAWLER_DIR} python"
    return sys.executable


def run(platform: str):
    """执行一次 MediaCrawler 采集"""
    if platform not in KEYWORDS:
        print(f"[ERROR] 未知平台: {platform}，可选: {', '.join(KEYWORDS.keys())}")
        return

    keywords = KEYWORDS[platform]
    name = PLATFORM_MAP.get(platform, platform)

    print(f"\n{'='*50}")
    print(f"  [{name}] 采集开始 - 关键词: {keywords}")
    print(f"{'='*50}\n")

    python_exe = get_venv_python()

    if "uv run" in python_exe:
        cmd = (python_exe + " main.py").split() + [
            "--platform", platform,
            "--type", "search",
            "--keywords", keywords,
            "--lt", "qrcode",
            "--headless", "yes" if HEADLESS else "no",
            "--get_comment", "yes",
            "--get_sub_comment", "no",
            "--crawler_max_notes_count", str(MAX_NOTES_PER_KEYWORD),
            "--max_comments_count_singlenotes", str(MAX_COMMENTS_PER_NOTE),
            "--save_data_option", SAVE_FORMAT,
        ]
    else:
        cmd = [python_exe, "main.py",
            "--platform", platform,
            "--type", "search",
            "--keywords", keywords,
            "--lt", "qrcode",
            "--headless", "yes" if HEADLESS else "no",
            "--get_comment", "yes",
            "--get_sub_comment", "no",
            "--crawler_max_notes_count", str(MAX_NOTES_PER_KEYWORD),
            "--max_comments_count_singlenotes", str(MAX_COMMENTS_PER_NOTE),
            "--save_data_option", SAVE_FORMAT,
        ]

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        cmd,
        cwd=MEDIA_CRAWLER_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    out = result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout
    err = result.stderr[-500:] if result.stderr else ""
    print(out)
    if result.returncode != 0 and err:
        print(f"[WARN] stderr: {err}")
    print(f"\n[ OK ] {name} 采集完成 (exit={result.returncode})\n")


if __name__ == "__main__":
    platforms = sys.argv[1:] if len(sys.argv) > 1 else list(KEYWORDS.keys())
    for p in platforms:
        run(p)

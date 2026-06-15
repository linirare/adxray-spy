"""一键跑完：采集所有平台 → 分析 → 出报告"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent

if __name__ == "__main__":
    # 1. 采集
    print("\n" + "★" * 50)
    print("  阶段 1/2: 数据采集")
    print("★" * 50)
    result = subprocess.run(
        [sys.executable, str(ROOT / "collect.py")],
        capture_output=False,
    )

    # 2. 分析
    print("\n" + "★" * 50)
    print("  阶段 2/2: 分析报告")
    print("★" * 50)
    result = subprocess.run(
        [sys.executable, str(ROOT / "analyze.py")],
        capture_output=False,
    )

    print("\n✅ 全部完成！")
    print(f"   输出目录: {ROOT / 'output'}")
    print(f"   原始数据: ~/MediaCrawler/data/")

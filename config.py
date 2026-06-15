"""竞品手游广告监控 - 配置文件"""

# 竞品游戏关键词（每个平台独立配置）
# 广告向关键词：分析素材形式/文案套路
KEYWORDS = {
    "dy": "狱国争霸,狱国争霸广告,狱国争霸推广,狱国争霸下载,狱国争霸礼包",  # 抖音
    "xhs": "狱国争霸,狱国争霸广告,狱国争霸推广",  # 小红书
    "ks": "狱国争霸",  # 快手
}

# MediaCrawler 路径
MEDIA_CRAWLER_DIR = "C:/Users/cth12/MediaCrawler"

# 输出目录
OUTPUT_DIR = "C:/Users/cth12/game_ad_analyzer/output"

# 采集配置
MAX_NOTES_PER_KEYWORD = 20    # 每个关键词最多采多少条
MAX_COMMENTS_PER_NOTE = 50    # 每条最多采多少评论
SAVE_FORMAT = "csv"           # csv / json / excel
HEADLESS = False              # 首次登录需要关闭无头模式，才能扫码

# 分析配置
TOP_N_WORDS = 30              # 词云 top N
MIN_COMMENT_LENGTH = 2        # 最短评论

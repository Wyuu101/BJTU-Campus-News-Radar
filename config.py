from __future__ import annotations

from pathlib import Path
from typing import Any


# 项目根目录，通常不需要修改。
BASE_DIR = Path(__file__).resolve().parent

# 本项目运行时数据目录，SQLite 数据库会放在这里。
DATA_DIR = BASE_DIR / "data"

# SQLite 数据库文件路径，用于保存已发现通知和 Web 多用户数据。
DB_PATH = DATA_DIR / "notice_monitor.sqlite3"

# Runner 日志等级；建议保持 INFO，调试总流程时可改成 DEBUG。
RUNNER_LOG_LEVEL = "INFO"

# 是否开启各网页板块脚本的调试输出；False 时只保留 runner 的进度日志。
DEBUG_SOURCES = False

# 单次 HTTP 请求超时时间，单位秒。
REQUEST_TIMEOUT_SECONDS = 15.0

# 同一个板块连续请求之间的等待时间，单位秒，避免访问过于频繁。
REQUEST_DELAY_SECONDS = 0.1

# 每个网页板块一个独立脚本；元组格式为：("模块导入路径", "入口函数名")。
SOURCE_ADAPTERS = [
    ("scrape_scripts.scrape_section_01", "crawl"),
    ("scrape_scripts.scrape_section_02", "crawl"),
    ("scrape_scripts.scrape_section_03", "crawl"),
    # ("scrape_scripts.scrape_section_04", "crawl"),
    # ("scrape_scripts.scrape_section_05", "crawl"),
    # ("scrape_scripts.scrape_section_06", "crawl"),
    # ("scrape_scripts.scrape_section_07", "crawl"),
    # ("scrape_scripts.scrape_section_08", "crawl"),
    # ("scrape_scripts.scrape_section_09", "crawl"),
    # ("scrape_scripts.scrape_section_10", "crawl"),
    # ("scrape_scripts.scrape_section_11", "crawl"),
    # ("scrape_scripts.scrape_section_12", "crawl"),
    # ("scrape_scripts.scrape_section_13", "crawl"),
    # ("scrape_scripts.scrape_section_14", "crawl"),
    # ("scrape_scripts.scrape_section_15", "crawl"),
]

# SMTP 服务器端口；SSL 通常为 465，STARTTLS 通常为 587。
SMTP_PORT = 465

# 是否使用 SMTP_SSL；如果改为 False，则使用 STARTTLS。
SMTP_USE_SSL = True

# SMTP 服务器地址；敏感本地覆盖值应写入 config_local.py。
SMTP_HOST = ""

# SMTP 登录用户名；敏感本地覆盖值应写入 config_local.py。
SMTP_USERNAME = ""

# SMTP 登录密码或授权码；敏感本地覆盖值应写入 config_local.py。
SMTP_PASSWORD = ""

# 发件人地址；敏感本地覆盖值应写入 config_local.py。
SMTP_FROM = ""

# 管理员邮箱；敏感本地覆盖值应写入 config_local.py。
ADMIN_EMAIL = ""


# 从本地私有配置文件覆盖敏感配置；config_local.py 应加入 .gitignore。
def _load_local_config() -> None:
    # 允许没有本地敏感配置时继续使用默认空配置运行。
    try:
        import config_local
    except ModuleNotFoundError:
        return

    # 仅加载大写配置项，避免把模块内部变量暴露到全局配置。
    local_values: dict[str, Any] = {
        key: getattr(config_local, key)
        for key in dir(config_local)
        if key.isupper()
    }
    globals().update(local_values)


# 加载本地私有配置，覆盖上方默认值。
_load_local_config()

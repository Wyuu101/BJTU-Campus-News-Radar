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
REQUEST_DELAY_SECONDS = 0.5

# 每个网页板块一个独立脚本；元组格式为：("模块导入路径", "入口函数名")。
SOURCE_ADAPTERS = [
    # 校园通用
    ("scrape_scripts.scrape_section_1", "crawl"),
    ("scrape_scripts.scrape_section_2", "crawl"),
    ("scrape_scripts.scrape_section_3", "crawl"),
    ("scrape_scripts.scrape_section_4", "crawl"),
    ("scrape_scripts.scrape_section_5", "crawl"),
    ("scrape_scripts.scrape_section_6", "crawl"),
    ("scrape_scripts.scrape_section_7", "crawl"),
    ("scrape_scripts.scrape_section_8", "crawl"),
    ("scrape_scripts.scrape_section_9", "crawl"),
    ("scrape_scripts.scrape_section_10", "crawl"),
    ("scrape_scripts.scrape_section_11", "crawl"),
    ("scrape_scripts.scrape_section_12", "crawl"),
    ("scrape_scripts.scrape_section_13", "crawl"),
    ("scrape_scripts.scrape_section_14", "crawl"),
    ("scrape_scripts.scrape_section_15", "crawl"),
    ("scrape_scripts.scrape_section_16", "crawl"),
    ("scrape_scripts.scrape_section_17", "crawl"),
    ("scrape_scripts.scrape_section_18", "crawl"),
    ("scrape_scripts.scrape_section_19", "crawl"),
    ("scrape_scripts.scrape_section_20", "crawl"),
    ("scrape_scripts.scrape_section_21", "crawl"),
    ("scrape_scripts.scrape_section_22", "crawl"),
    ("scrape_scripts.scrape_section_23", "crawl"),
    ("scrape_scripts.scrape_section_24", "crawl"),
    ("scrape_scripts.scrape_section_25", "crawl"),
    ("scrape_scripts.scrape_section_26", "crawl"),
    ("scrape_scripts.scrape_section_27", "crawl"),

    # 电信
    ("scrape_scripts.scrape_section_80_01", "crawl"),
    ("scrape_scripts.scrape_section_80_02", "crawl"),
    ("scrape_scripts.scrape_section_80_03", "crawl"),
    ("scrape_scripts.scrape_section_80_04", "crawl"),
    ("scrape_scripts.scrape_section_80_05", "crawl"),
    ("scrape_scripts.scrape_section_80_06", "crawl"),
    ("scrape_scripts.scrape_section_80_07", "crawl"),

    # 经管
    ("scrape_scripts.scrape_section_81_01", "crawl"),
    ("scrape_scripts.scrape_section_81_02", "crawl"),
    ("scrape_scripts.scrape_section_81_03", "crawl"),
    ("scrape_scripts.scrape_section_81_04", "crawl"),
    ("scrape_scripts.scrape_section_81_05", "crawl"),
    ("scrape_scripts.scrape_section_81_06", "crawl"),
    ("scrape_scripts.scrape_section_81_07", "crawl"),
    ("scrape_scripts.scrape_section_81_08", "crawl"),
    ("scrape_scripts.scrape_section_81_09", "crawl"),
    ("scrape_scripts.scrape_section_81_10", "crawl"),
    ("scrape_scripts.scrape_section_81_11", "crawl"),
    ("scrape_scripts.scrape_section_81_12", "crawl"),
    ("scrape_scripts.scrape_section_81_13", "crawl"),
    ("scrape_scripts.scrape_section_81_14", "crawl"),

    # 自动化与智能
    ("scrape_scripts.scrape_section_82_01", "crawl"),
    ("scrape_scripts.scrape_section_82_02", "crawl"),
    ("scrape_scripts.scrape_section_82_03", "crawl"),
    ("scrape_scripts.scrape_section_82_04", "crawl"),
    ("scrape_scripts.scrape_section_82_05", "crawl"),
    ("scrape_scripts.scrape_section_82_06", "crawl"),
    ("scrape_scripts.scrape_section_82_07", "crawl"),
    ("scrape_scripts.scrape_section_82_08", "crawl"),
    ("scrape_scripts.scrape_section_82_09", "crawl"),
    ("scrape_scripts.scrape_section_82_10", "crawl"),
    ("scrape_scripts.scrape_section_82_11", "crawl"),

    # 交运
    ("scrape_scripts.scrape_section_83_01", "crawl"),
    ("scrape_scripts.scrape_section_83_02", "crawl"),
    ("scrape_scripts.scrape_section_83_03", "crawl"),
    ("scrape_scripts.scrape_section_83_04", "crawl"),
    ("scrape_scripts.scrape_section_83_05", "crawl"),
    ("scrape_scripts.scrape_section_83_06", "crawl"),
    ("scrape_scripts.scrape_section_83_07", "crawl"),
    ("scrape_scripts.scrape_section_83_08", "crawl"),

    # 计算机
    ("scrape_scripts.scrape_section_84_01", "crawl"),
    ("scrape_scripts.scrape_section_84_02", "crawl"),
    ("scrape_scripts.scrape_section_84_03", "crawl"),
    ("scrape_scripts.scrape_section_84_04", "crawl"),
    ("scrape_scripts.scrape_section_84_05", "crawl"),
    ("scrape_scripts.scrape_section_84_06", "crawl"),
    ("scrape_scripts.scrape_section_84_07", "crawl"),
    ("scrape_scripts.scrape_section_84_08", "crawl"),
    ("scrape_scripts.scrape_section_84_09", "crawl"),
    ("scrape_scripts.scrape_section_84_10", "crawl"),
    ("scrape_scripts.scrape_section_84_11", "crawl"),
    ("scrape_scripts.scrape_section_84_12", "crawl"),
    ("scrape_scripts.scrape_section_84_13", "crawl"),
    ("scrape_scripts.scrape_section_84_14", "crawl"),
    ("scrape_scripts.scrape_section_84_15", "crawl"),

    # 软件学院
    ("scrape_scripts.scrape_section_85_01", "crawl"),
    ("scrape_scripts.scrape_section_85_02", "crawl"),
    ("scrape_scripts.scrape_section_85_03", "crawl"),
    ("scrape_scripts.scrape_section_85_04", "crawl"),
    ("scrape_scripts.scrape_section_85_05", "crawl"),
    ("scrape_scripts.scrape_section_85_06", "crawl"),
    ("scrape_scripts.scrape_section_85_07", "crawl"),
    ("scrape_scripts.scrape_section_85_08", "crawl"),
    ("scrape_scripts.scrape_section_85_09", "crawl"),
    ("scrape_scripts.scrape_section_85_10", "crawl"),
    ("scrape_scripts.scrape_section_85_11", "crawl"),
    ("scrape_scripts.scrape_section_85_12", "crawl"),
    ("scrape_scripts.scrape_section_85_13", "crawl"),
    ("scrape_scripts.scrape_section_85_14", "crawl"),
    ("scrape_scripts.scrape_section_85_15", "crawl"),

    # 法学院
    ("scrape_scripts.scrape_section_86_01", "crawl"),
    ("scrape_scripts.scrape_section_86_02", "crawl"),
    ("scrape_scripts.scrape_section_86_03", "crawl"),
    ("scrape_scripts.scrape_section_86_04", "crawl"),
    ("scrape_scripts.scrape_section_86_05", "crawl"),
    ("scrape_scripts.scrape_section_86_06", "crawl"),
    ("scrape_scripts.scrape_section_86_07", "crawl"),
    ("scrape_scripts.scrape_section_86_08", "crawl"),
    ("scrape_scripts.scrape_section_86_09", "crawl"),
    ("scrape_scripts.scrape_section_86_10", "crawl"),
    ("scrape_scripts.scrape_section_86_11", "crawl"),
    ("scrape_scripts.scrape_section_86_12", "crawl"),
    ("scrape_scripts.scrape_section_86_13", "crawl"),
    ("scrape_scripts.scrape_section_86_14", "crawl"),

    # 数统
    ("scrape_scripts.scrape_section_87_01", "crawl"),
    ("scrape_scripts.scrape_section_87_02", "crawl"),
    ("scrape_scripts.scrape_section_87_03", "crawl"),
    ("scrape_scripts.scrape_section_87_04", "crawl"),
]

# 登录验证码 SMTP 服务器端口；SSL 通常为 465，STARTTLS 通常为 587。
SMTP_PORT = 465

# 登录验证码是否使用 SMTP_SSL；如果改为 False，则使用 STARTTLS。
SMTP_USE_SSL = True

# 登录验证码 SMTP 服务器地址；敏感本地覆盖值应写入 config_local.py。
SMTP_HOST = ""

# 登录验证码 SMTP 登录用户名；敏感本地覆盖值应写入 config_local.py。
SMTP_USERNAME = ""

# 登录验证码 SMTP 登录密码或授权码；敏感本地覆盖值应写入 config_local.py。
SMTP_PASSWORD = ""

# 登录验证码发件人地址；敏感本地覆盖值应写入 config_local.py。
SMTP_FROM = ""

# 登录验证码 SMTP 每分钟最多发送数量；超过后进入全局冷却。
EMAIL_SMTP_MAX_SENDS_PER_MINUTE = 20

# 登录验证码 SMTP 触发全局频限后的冷却时间，单位秒。
EMAIL_SMTP_GLOBAL_COOLDOWN_SECONDS = 180

# 全局冷却期间用于审查单个 IP 请求频次的窗口，单位秒。
EMAIL_SMTP_IP_BAN_WINDOW_SECONDS = 180

# 全局冷却期间单个 IP 在审查窗口内超过该次数后加入黑名单。
EMAIL_SMTP_IP_BAN_THRESHOLD = 10

# 是否启用验证码请求 IP 黑名单功能；默认关闭，避免误伤正常用户。
ENABLE_LOGIN_IP_BLACKLIST = False

# 可接收通知的最大活跃用户数；达到上限后不再接收新邮箱。
REGISTRATION_USER_LIMIT = 300

# 站点根地址，用于 runner 在后台邮件中生成可点击的页面链接；部署后改为正式域名。
SITE_BASE_URL = "http://127.0.0.1:8000"

# 每日通知 SMTP 服务器端口；用于 runner 发送订阅通知和异常报告。
NOTIFICATION_SMTP_PORT = 465

# 每日通知是否使用 SMTP_SSL；如果改为 False，则使用 STARTTLS。
NOTIFICATION_SMTP_USE_SSL = True

# 每日通知 SMTP 服务器地址；敏感本地覆盖值应写入 config_local.py。
NOTIFICATION_SMTP_HOST = ""

# 每日通知 SMTP 登录用户名；敏感本地覆盖值应写入 config_local.py。
NOTIFICATION_SMTP_USERNAME = ""

# 每日通知 SMTP 登录密码或授权码；敏感本地覆盖值应写入 config_local.py。
NOTIFICATION_SMTP_PASSWORD = ""

# 每日通知发件人地址；敏感本地覆盖值应写入 config_local.py。
NOTIFICATION_SMTP_FROM = ""

# 每日通知 SMTP 每分钟最大发送数量；默认小于 150 次/分钟。
NOTIFICATION_SMTP_MAX_SENDS_PER_MINUTE = 149

# 每日整合通知预计发送时间，仅用于 Web 页面提示文案展示。
DAILY_NOTIFICATION_DISPLAY_TIME = "18:30"

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

from __future__ import annotations

from pathlib import Path
from typing import Any


# 项目根目录，通常不需要修改。
BASE_DIR = Path(__file__).resolve().parent

# 本项目运行时数据目录，SQLite 数据库会放在这里。
DATA_DIR = BASE_DIR / "data"

# SQLite 数据库文件路径，用于保存已发现通知和待发送邮件队列。
DB_PATH = DATA_DIR / "notice_monitor.sqlite3"

# Runner 日志等级；建议保持 INFO，调试总流程时可改成 DEBUG。
RUNNER_LOG_LEVEL = "INFO"

# 是否开启各网页板块脚本的调试输出；False 时只保留 runner 的进度日志。
DEBUG_SOURCES = True

# 单次 HTTP 请求超时时间，单位秒。
REQUEST_TIMEOUT_SECONDS = 15.0

# 同一个板块连续请求之间的等待时间，单位秒，避免访问过于频繁。
REQUEST_DELAY_SECONDS = 0.1

# 每个网页板块一个独立脚本；元组格式为：("模块名", "入口函数名")。
SOURCE_ADAPTERS = [
    ("scrap_section_01", "crawl"),
    ("scrap_section_15", "crawl"),

]

# SMTP 服务器地址，例如 QQ 邮箱可填 "smtp.qq.com"。
SMTP_HOST = ""

# SMTP 服务器端口；SSL 通常为 465，STARTTLS 通常为 587。
SMTP_PORT = 465

# SMTP 登录用户名，通常是完整邮箱地址。
SMTP_USERNAME = ""

# SMTP 登录密码或授权码；多数邮箱服务需要填写授权码而不是网页登录密码。
SMTP_PASSWORD = ""

# 发件人地址；一般与 SMTP_USERNAME 相同。
SMTP_FROM = ""

# 收件人地址列表；可填写多个邮箱。
SMTP_TO = [
]

# 是否使用 SMTP_SSL；如果改为 False，则使用 STARTTLS。
SMTP_USE_SSL = True


# 从本地私有配置文件覆盖敏感配置；config_local.py 应加入 .gitignore。
def _load_local_config() -> None:
    try:
        import config_local
    except ModuleNotFoundError:
        return

    local_values: dict[str, Any] = {
        key: getattr(config_local, key)
        for key in dir(config_local)
        if key.isupper()
    }
    globals().update(local_values)


_load_local_config()

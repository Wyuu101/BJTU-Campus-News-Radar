from __future__ import annotations

from pathlib import Path

import config


# 项目根目录，复用顶层 config 中的路径定义。
BASE_DIR = config.BASE_DIR

# Web 包根目录，用于后续扩展模板或静态文件路径。
WEB_DIR = Path(__file__).resolve().parent.parent

# 确保 SQLite 所在数据目录存在，避免 Django 初始化数据库时报错。
config.DATA_DIR.mkdir(parents=True, exist_ok=True)

# Django 密钥；生产环境必须通过 local_settings.py 覆盖。
SECRET_KEY = "unsafe-dev-placeholder"

# 开发模式开关；生产部署时应在正式配置中关闭。
DEBUG = True

# 允许访问的主机名；本地开发默认只允许 localhost。
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1"
]

# Django 应用列表，当前只启用必要内置组件和 notice_app。
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "captcha",
    "web.notice_app",
]

# Django 中间件列表，保留 session、CSRF 与基础安全中间件。
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# 根 URL 路由配置模块。
ROOT_URLCONF = "web.bjtu_notice_site.urls"

# WSGI 应用入口，供生产 WSGI 容器加载。
WSGI_APPLICATION = "web.bjtu_notice_site.wsgi.application"

# 模板加载配置，使用应用内 templates 目录。
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

# 数据库配置，Web 表与爬虫表共用同一个 SQLite 文件。
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": config.DB_PATH,
    }
}

# Django 界面与系统语言。
LANGUAGE_CODE = "zh-hans"

# 业务默认时区，和项目当前部署地区保持一致。
TIME_ZONE = "Asia/Shanghai"

# 启用 Django 国际化机制。
USE_I18N = True

# 使用带时区的 datetime 存储和计算。
USE_TZ = True

# 静态资源根目录
STATIC_ROOT = BASE_DIR / "web" / "staticfiles"

# 静态资源访问前缀。
STATIC_URL = "static/"

# 额外静态资源目录预留；当前静态资源均放在应用内部。
STATICFILES_DIRS: list[Path] = []

# 默认主键字段类型。
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Session cookie 禁止被 JavaScript 读取，降低 XSS 后的会话泄露风险。
SESSION_COOKIE_HTTPONLY = True

# Session cookie SameSite 策略，兼顾基本 CSRF 风险和本地可用性。
SESSION_COOKIE_SAMESITE = "Lax"

# Session 有效期，当前为 14 天。
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14

# CSRF cookie SameSite 策略。
CSRF_COOKIE_SAMESITE = "Lax"

# 邮箱登录验证码长度。
EMAIL_CODE_LENGTH = 8

# 邮箱登录验证码有效期，单位秒。
EMAIL_CODE_TTL_SECONDS = 180

# 邮箱验证码发送冷却时间，单位秒。
EMAIL_CODE_COOLDOWN_SECONDS = 60

# 单个验证码允许尝试的最大次数。
EMAIL_CODE_MAX_ATTEMPTS = 6

# 图形验证码图片刷新接口最小请求间隔，单位秒。
CAPTCHA_REFRESH_RATE_LIMIT_SECONDS = 1.0

# 图形验证码字符长度。
CAPTCHA_LENGTH = 5

# 图形验证码有效期，单位分钟。
CAPTCHA_TIMEOUT = 3

# 图形验证码图片尺寸，宽高单位为像素。
CAPTCHA_IMAGE_SIZE = (150, 52)

# 图形验证码字体大小。
CAPTCHA_FONT_SIZE = 30

# 图形验证码字符旋转角度范围。
CAPTCHA_LETTER_ROTATION = (-42, 42)

# 图形验证码背景颜色。
CAPTCHA_BACKGROUND_COLOR = "#fff7ed"

# 图形验证码默认前景颜色。
CAPTCHA_FOREGROUND_COLOR = "#5f4735"

# 图形验证码字符颜色函数，让每个字符颜色轻微变化。
CAPTCHA_LETTER_COLOR_FUNCT = "web.notice_app.captcha_utils.captcha_letter_color"

# 图形验证码挑战生成函数，避免只出现单一小写字母。
CAPTCHA_CHALLENGE_FUNCT = "web.notice_app.captcha_utils.captcha_challenge"

# 图形验证码噪声函数，叠加线条、点和额外干扰线。
CAPTCHA_NOISE_FUNCTIONS = (
    "captcha.helpers.noise_arcs",
    "captcha.helpers.noise_dots",
    "web.notice_app.captcha_utils.captcha_noise_lines",
)

# 图形验证码滤镜函数，保持库默认平滑处理。
CAPTCHA_FILTER_FUNCTIONS = ("captcha.helpers.post_smooth",)

# 邮箱对称加密密钥文件路径；真实密钥文件不提交仓库。
EMAIL_ENCRYPTION_KEY_PATH = BASE_DIR / "web" / "secrets" / "email_encryption.key"

# 从本地敏感配置覆盖 Django 密钥等值；local_settings.py 应加入 .gitignore。
try:
    from .local_settings import *  # noqa: F403
except ModuleNotFoundError:
    pass

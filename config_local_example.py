from __future__ import annotations


# 登录验证码 SMTP 服务器地址，例如 QQ 邮箱可填 "smtp.qq.com"。
SMTP_HOST = "smtp.example.com"

# 登录验证码 SMTP 登录用户名，通常是完整邮箱地址。
SMTP_USERNAME = "sender@example.com"

# 登录验证码 SMTP 登录密码或授权码；多数邮箱服务需要填写授权码而不是网页登录密码。
SMTP_PASSWORD = "replace-with-email-auth-code"

# 登录验证码发件人地址；一般与 SMTP_USERNAME 相同。
SMTP_FROM = "sender@example.com"

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

# 每日通知 SMTP 服务器地址。
NOTIFICATION_SMTP_HOST = "smtp.example.com"

# 每日通知 SMTP 服务器端口；SSL 通常为 465，STARTTLS 通常为 587。
NOTIFICATION_SMTP_PORT = 465

# 每日通知是否使用 SMTP_SSL；如果改为 False，则使用 STARTTLS。
NOTIFICATION_SMTP_USE_SSL = True

# 每日通知 SMTP 登录用户名，建议使用专门的通知邮箱。
NOTIFICATION_SMTP_USERNAME = "daily-notice@example.com"

# 每日通知 SMTP 登录密码或授权码。
NOTIFICATION_SMTP_PASSWORD = "replace-with-daily-notice-auth-code"

# 每日通知发件人地址；一般与 NOTIFICATION_SMTP_USERNAME 相同。
NOTIFICATION_SMTP_FROM = "daily-notice@example.com"

# 每日通知 SMTP 每分钟最大发送数量；默认小于 150 次/分钟。
NOTIFICATION_SMTP_MAX_SENDS_PER_MINUTE = 149

# 管理员邮箱，用于接收 runner 异常报告。
ADMIN_EMAIL = "admin@example.com"

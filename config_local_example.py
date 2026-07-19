from __future__ import annotations


# SMTP 服务器地址，例如 QQ 邮箱可填 "smtp.qq.com"。
SMTP_HOST = "smtp.example.com"

# SMTP 登录用户名，通常是完整邮箱地址。
SMTP_USERNAME = "sender@example.com"

# SMTP 登录密码或授权码；多数邮箱服务需要填写授权码而不是网页登录密码。
SMTP_PASSWORD = "replace-with-email-auth-code"

# 发件人地址；一般与 SMTP_USERNAME 相同。
SMTP_FROM = "sender@example.com"

# 默认收件人地址列表；Web 多用户模式下通常不需要在这里配置真实用户。
SMTP_TO = [
    "receiver@example.com",
]

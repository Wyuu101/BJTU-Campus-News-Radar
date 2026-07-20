from __future__ import annotations

from django.db import models


# Web 订阅用户表，邮箱正文加密存储，邮箱哈希用于查重和查询。
class Subscriber(models.Model):
    # 规范化邮箱的 SHA256 哈希，用于唯一识别用户且避免明文查询。
    email_hash = models.CharField(max_length=64, unique=True, db_index=True)

    # Fernet 加密后的邮箱地址，实际发送邮件前再解密。
    encrypted_email = models.TextField()

    # 用户已勾选的 SECTION_NAME 列表。
    preferences = models.JSONField(default=list, blank=True)

    # 用户已见过的 SECTION_NAME 列表，用于新增板块默认勾选。
    known_sections = models.JSONField(default=list, blank=True)

    # 用户是否仍接收通知；注销账户会置为 False。
    is_active = models.BooleanField(default=True)

    # 用户首次创建时间。
    created_at = models.DateTimeField(auto_now_add=True)

    # 用户订阅或登录信息最近更新时间。
    updated_at = models.DateTimeField(auto_now=True)

    # 用户最近一次验证码登录成功时间。
    last_login_at = models.DateTimeField(null=True, blank=True)

    # 数据库表名和默认排序规则。
    class Meta:
        db_table = "web_subscribers"
        ordering = ["-updated_at"]


# 邮箱验证码表，保存短期登录验证码的哈希、冷却和尝试次数。
class EmailVerification(models.Model):
    # 规范化邮箱的 SHA256 哈希。
    email_hash = models.CharField(max_length=64, db_index=True)

    # Fernet 加密后的邮箱地址，便于审计或后续扩展。
    encrypted_email = models.TextField()

    # 验证码 SHA256 哈希，不保存明文验证码。
    code_hash = models.CharField(max_length=64)

    # 验证码过期时间。
    expires_at = models.DateTimeField()

    # 下一次允许发送验证码的时间。
    cooldown_until = models.DateTimeField()

    # 发起验证码请求的客户端 IP，用于异常频次审查。
    client_ip = models.GenericIPAddressField(null=True, blank=True)

    # 当前验证码已尝试校验次数。
    attempts = models.PositiveSmallIntegerField(default=0)

    # 验证码被成功使用的时间。
    used_at = models.DateTimeField(null=True, blank=True)

    # 验证码记录创建时间。
    created_at = models.DateTimeField(auto_now_add=True)

    # 数据库表名和邮箱查询索引。
    class Meta:
        db_table = "web_email_verifications"
        indexes = [
            models.Index(fields=["email_hash", "-created_at"], name="web_ev_hash_created_idx"),
            models.Index(fields=["client_ip", "-created_at"], name="web_ev_ip_created_idx"),
        ]


# 邮箱验证码请求日志表，包含成功发送、限流拦截和黑名单拦截请求。
class EmailVerificationRequest(models.Model):
    # 规范化邮箱的 SHA256 哈希；邮箱格式不合法时可为空。
    email_hash = models.CharField(max_length=64, blank=True, db_index=True)

    # 发起请求的客户端 IP。
    client_ip = models.GenericIPAddressField(null=True, blank=True, db_index=True)

    # 请求是否被限流或黑名单拦截。
    was_blocked = models.BooleanField(default=False)

    # 拦截原因，便于后续排查。
    block_reason = models.CharField(max_length=80, blank=True)

    # 请求发生时间。
    created_at = models.DateTimeField(auto_now_add=True)

    # 数据库表名和 IP 时间窗口查询索引。
    class Meta:
        db_table = "web_email_verification_requests"
        indexes = [
            models.Index(fields=["client_ip", "-created_at"], name="web_evr_ip_created_idx"),
        ]


# 邮箱验证码 IP 黑名单表，命中后拒绝验证码发送和验证码登录请求。
class EmailVerificationIpBlacklist(models.Model):
    # 被封禁的客户端 IP。
    client_ip = models.GenericIPAddressField(unique=True, db_index=True)

    # 封禁原因。
    reason = models.CharField(max_length=160, blank=True)

    # 封禁创建时间。
    created_at = models.DateTimeField(auto_now_add=True)

    # 数据库表名和默认排序。
    class Meta:
        db_table = "web_email_verification_ip_blacklist"
        ordering = ["-created_at"]


# 登录验证码 SMTP 全局频限状态表，记录触发后的冷却时间。
class EmailSmtpRateLimitState(models.Model):
    # 状态名称，当前用于区分登录验证码 SMTP。
    name = models.CharField(max_length=40, unique=True)

    # 冷却截止时间；为空或已过期时表示未处于冷却。
    cooldown_until = models.DateTimeField(null=True, blank=True)

    # 记录最近更新时间。
    updated_at = models.DateTimeField(auto_now=True)

    # 数据库表名。
    class Meta:
        db_table = "web_email_smtp_rate_limit_state"


# 每日新增通知统计表，供首页趋势图读取。
class DailyMetric(models.Model):
    # 统计日期，每天一条。
    date = models.DateField(unique=True)

    # 当日 runner 新发现通知的累计数量。
    new_notice_count = models.PositiveIntegerField(default=0)

    # 统计记录创建时间。
    created_at = models.DateTimeField(auto_now_add=True)

    # 统计记录最近更新时间。
    updated_at = models.DateTimeField(auto_now=True)

    # 数据库表名和默认日期升序排序。
    class Meta:
        db_table = "web_daily_metrics"
        ordering = ["date"]

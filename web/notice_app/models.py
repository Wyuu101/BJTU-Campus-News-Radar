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
        ]


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

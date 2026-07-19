from __future__ import annotations

import hashlib
import random
import smtplib
from datetime import timedelta
from email.message import EmailMessage
from typing import Sequence

from django.conf import settings
from django.db.models import F
from django.utils import timezone

import config
from data_formats import QueuedNotice
from email_notifier import EmailNotifier
from source_registry import discover_sections
from web.notice_app.crypto import decrypt_email, email_hash, encrypt_email, normalize_email
from web.notice_app.models import DailyMetric, EmailVerification, Subscriber


# 返回当前项目中可展示给用户的去重板块名。
def get_section_names() -> list[str]:
    return [section.section_name for section in discover_sections()]


# 新用户默认订阅当前所有板块。
def get_default_preferences() -> list[str]:
    return get_section_names()


# 获取或创建订阅用户，已注销用户重新登录时自动恢复。
def get_or_create_subscriber(email: str) -> Subscriber:
    # 统一邮箱格式，并用哈希作为查询键。
    normalized = normalize_email(email)
    subscriber, created = Subscriber.objects.get_or_create(
        email_hash=email_hash(normalized),
        defaults={
            "encrypted_email": encrypt_email(normalized),
            "preferences": get_default_preferences(),
            "known_sections": get_default_preferences(),
            "is_active": True,
        },
    )

    # 重新登录已注销用户时恢复激活状态，并刷新邮箱密文。
    if not created and not subscriber.is_active:
        subscriber.is_active = True
        subscriber.encrypted_email = encrypt_email(normalized)

    # 老用户登录时刷新最近登录时间。
    if not created:
        subscriber.last_login_at = timezone.now()
        subscriber.save(update_fields=["is_active", "encrypted_email", "last_login_at", "updated_at"])
    return subscriber


# 返回用户实际生效的订阅偏好，并把新增板块默认加入勾选。
def get_effective_preferences(subscriber: Subscriber) -> list[str]:
    # 读取当前后端真实可订阅板块和用户历史已见板块。
    available = get_section_names()
    known = set(subscriber.known_sections or [])
    selected = set(subscriber.preferences or [])

    # 新增板块对老用户默认勾选，避免新增爬虫后用户无感漏收。
    new_sections = [section for section in available if section not in known]
    if new_sections:
        selected.update(new_sections)
        subscriber.preferences = [section for section in available if section in selected]
        subscriber.known_sections = available
        subscriber.save(update_fields=["preferences", "known_sections", "updated_at"])
    return [section for section in available if section in selected]


# 创建邮箱验证码记录并发送验证码邮件。
def request_login_code(email: str, client_ip: str | None = None) -> tuple[bool, str, int]:
    # 规范化邮箱并读取当前时间。
    normalized = normalize_email(email)
    now = timezone.now()

    # 冷却时间未结束时拒绝重复发送。
    last_code = EmailVerification.objects.filter(email_hash=email_hash(normalized)).order_by("-created_at").first()
    if last_code and last_code.cooldown_until > now and last_code.used_at is None:
        seconds = int((last_code.cooldown_until - now).total_seconds())
        return False, f"验证码已经在路上了，{seconds} 秒后可以再次发送。", seconds

    # 生成固定长度数字验证码。
    code = f"{random.SystemRandom().randrange(10 ** settings.EMAIL_CODE_LENGTH):0{settings.EMAIL_CODE_LENGTH}d}"

    # 保存验证码哈希、过期时间和冷却时间。
    verification = EmailVerification.objects.create(
        email_hash=email_hash(normalized),
        encrypted_email=encrypt_email(normalized),
        code_hash=_hash_code(code),
        expires_at=now + timedelta(seconds=settings.EMAIL_CODE_TTL_SECONDS),
        cooldown_until=now + timedelta(seconds=settings.EMAIL_CODE_COOLDOWN_SECONDS),
        client_ip=client_ip,
    )

    # 发送验证码邮件；SMTP 未配置时函数内部会安全跳过。
    _send_verification_email(normalized, code)
    return True, "验证码已发送，请留意邮箱。", int((verification.cooldown_until - now).total_seconds())


# 校验邮箱验证码，成功后返回订阅用户对象。
def verify_login_code(email: str, code: str) -> tuple[bool, str, Subscriber | None]:
    # 规范化邮箱并查找最新未使用验证码。
    normalized = normalize_email(email)
    now = timezone.now()
    verification = EmailVerification.objects.filter(
        email_hash=email_hash(normalized),
        used_at__isnull=True,
    ).order_by("-created_at").first()

    # 没有可用验证码时要求用户先获取验证码。
    if verification is None:
        return False, "请先获取邮箱验证码。", None

    # 过期验证码不可继续使用。
    if verification.expires_at < now:
        return False, "验证码已过期，请重新获取。", None

    # 超过尝试次数后要求重新获取，减少爆破风险。
    if verification.attempts >= settings.EMAIL_CODE_MAX_ATTEMPTS:
        return False, "尝试次数过多，请重新获取验证码。", None

    # 每次校验都增加尝试次数。
    verification.attempts += 1

    # 哈希比对失败时保存尝试次数并返回错误。
    if verification.code_hash != _hash_code(code.strip()):
        verification.save(update_fields=["attempts"])
        return False, "验证码不对，再检查一下邮箱里的 8 位数字。", None

    # 标记验证码已使用，防止重复登录复用。
    verification.used_at = now
    verification.save(update_fields=["attempts", "used_at"])

    # 登录成功后获取或创建订阅用户。
    subscriber = get_or_create_subscriber(normalized)
    subscriber.last_login_at = now
    subscriber.save(update_fields=["last_login_at", "updated_at"])
    return True, "登录成功。", subscriber


# 保存用户订阅偏好，只接受后端存在的板块名。
def update_preferences(subscriber: Subscriber, selected_sections: Sequence[str]) -> None:
    # 使用后端板块集合过滤前端提交值，防止非法 section 被写入数据库。
    available_sections = set(get_section_names())
    selected = [section for section in selected_sections if section in available_sections]
    subscriber.preferences = selected

    # 保存时记录当前已见板块，用于后续新增板块默认勾选。
    subscriber.known_sections = list(available_sections)
    subscriber.save(update_fields=["preferences", "known_sections", "updated_at"])


# 软注销订阅用户，停止后续邮件推送。
def deactivate_subscriber(subscriber: Subscriber) -> None:
    subscriber.is_active = False
    subscriber.preferences = []
    subscriber.save(update_fields=["is_active", "preferences", "updated_at"])


# 将 runner 本轮新增通知数累加到当天统计。
def record_new_notice_count(count: int) -> None:
    if count <= 0:
        return

    # 按本地日期创建或读取当天统计记录。
    metric, _created = DailyMetric.objects.get_or_create(
        date=timezone.localdate(),
        defaults={"new_notice_count": 0},
    )

    # 用数据库自增表达式避免并发运行 runner 时覆盖计数。
    DailyMetric.objects.filter(pk=metric.pk).update(new_notice_count=F("new_notice_count") + count)


# 读取首页公开统计数据，包括近 days 天趋势和当前用户数。
def get_public_stats(days: int = 10) -> dict[str, object]:
    # 计算包含今天在内的日期窗口。
    today = timezone.localdate()
    start_date = today - timedelta(days=days - 1)

    # 读取窗口内已有统计，缺失日期稍后补 0。
    existing = {
        metric.date: metric.new_notice_count
        for metric in DailyMetric.objects.filter(date__gte=start_date, date__lte=today)
    }

    # 生成前端曲线图需要的连续日期点。
    points = []
    for offset in range(days):
        current = start_date + timedelta(days=offset)
        points.append({"date": current.isoformat(), "count": existing.get(current, 0)})

    # 返回趋势点和当前激活用户数。
    return {
        "points": points,
        "currentUserCount": Subscriber.objects.filter(is_active=True).count(),
    }


# 按 Web 用户订阅偏好逐个过滤并发送待通知队列。
def dispatch_pending_notices(notices: Sequence[QueuedNotice]) -> bool:
    if not notices:
        return True

    # 初始化邮件通知器，并读取当前激活订阅用户。
    notifier = EmailNotifier()
    active_subscribers = Subscriber.objects.filter(is_active=True)
    sent_any = False
    had_target = False

    # 为每个用户解密邮箱并按其订阅板块过滤通知。
    for subscriber in active_subscribers:
        try:
            email = decrypt_email(subscriber.encrypted_email)
        except Exception:
            continue

        # 只发送用户勾选板块对应的新通知。
        selected_sections = get_effective_preferences(subscriber)
        target_notices = [notice for notice in notices if notice.section in selected_sections]
        if not target_notices:
            continue
        had_target = True
        sent_any = notifier.send_to_recipient(email, target_notices) or sent_any

    # 至少有一个用户发送成功时，本轮队列可标记已发送。
    if sent_any:
        return True

    # 有用户但没有任何用户命中订阅时，也视为本轮无需发送。
    if active_subscribers.exists() and not had_target:
        return True

    # 有目标用户但全部发送失败时返回 False，保留队列重试。
    if active_subscribers.exists():
        return False

    # 没有 Web 用户时，回退到 config.SMTP_TO 的旧发送逻辑。
    return notifier.send(notices)


# 对验证码做 SHA256 哈希，数据库不保存明文验证码。
def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


# 发送邮箱登录验证码邮件。
def _send_verification_email(recipient: str, code: str) -> None:
    # SMTP 配置不完整时跳过发送，便于本地开发。
    if not config.SMTP_HOST or not config.SMTP_FROM or not config.SMTP_USERNAME or not config.SMTP_PASSWORD:
        return

    # 构造同时包含纯文本和 HTML 的验证码邮件。
    message = EmailMessage()
    message["Subject"] = "BJTU Notice Monitor 登录验证码"
    message["From"] = config.SMTP_FROM
    message["To"] = recipient
    message.set_content(
        f"您的登录验证码是：{code}\n\n验证码 3 分钟内有效。如非本人操作，请忽略本邮件。"
    )
    message.add_alternative(_build_code_html(code), subtype="html")

    # 根据全局配置选择 SMTP_SSL 或 STARTTLS。
    if config.SMTP_USE_SSL:
        with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT) as smtp:
            smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            smtp.send_message(message, from_addr=config.SMTP_FROM, to_addrs=[recipient])
    else:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            smtp.send_message(message, from_addr=config.SMTP_FROM, to_addrs=[recipient])


# 构造验证码邮件 HTML 正文。
def _build_code_html(code: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<body style="margin:0;padding:0;background:#f7f3ee;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;color:#292524;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="padding:34px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="560" cellspacing="0" cellpadding="0" border="0" style="max-width:560px;width:100%;background:#fffaf5;border:1px solid #eadfd3;border-radius:22px;box-shadow:0 22px 52px rgba(120,94,70,.14);">
          <tr>
            <td style="padding:30px;">
              <div style="font-size:13px;color:#9a7b5f;margin-bottom:10px;">邮箱验证码</div>
              <h1 style="margin:0 0 16px;font-size:24px;line-height:1.3;color:#2f261f;">欢迎回来，请确认这次登录</h1>
              <p style="margin:0 0 22px;font-size:14px;line-height:1.8;color:#68584a;">请在 3 分钟内输入下面的 8 位验证码，完成后就能继续管理你的通知偏好。</p>
              <div style="letter-spacing:8px;font-size:34px;font-weight:800;color:#2f261f;background:#f3eadf;border-radius:18px;padding:18px 20px;text-align:center;">{code}</div>
              <p style="margin:22px 0 0;font-size:13px;line-height:1.8;color:#8a7a6b;">如非本人操作，请忽略本邮件。为了账户安全，请不要把验证码转发给他人。</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

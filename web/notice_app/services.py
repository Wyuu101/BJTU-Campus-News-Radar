from __future__ import annotations

import hashlib
import logging
import random
import smtplib
from dataclasses import dataclass, field
from datetime import timedelta
from email.message import EmailMessage
from typing import Sequence
from urllib.parse import quote

from django.conf import settings
from django.core import signing
from django.db.models import F
from django.utils import timezone

import config
from data_formats import NoticeRecord
from email_notifier import EmailNotifier
from source_registry import discover_sections
from web.notice_app.crypto import decrypt_email, email_hash, encrypt_email, normalize_email
from web.notice_app.models import (
    DailyMetric,
    EmailSmtpRateLimitState,
    EmailVerification,
    EmailVerificationIpBlacklist,
    EmailVerificationRequest,
    Subscriber,
)


logger = logging.getLogger(__name__)


@dataclass
class MailDispatchSummary:
    """记录本轮订阅邮件分发的统计结果。"""

    success_count: int = 0
    failure_count: int = 0
    failures: list[tuple[str, str]] = field(default_factory=list)


# 登录验证码 SMTP 全局频限状态名称。
EMAIL_SMTP_RATE_LIMIT_STATE_NAME = "login_verification"

# 用户数量达到上限后的统一提示。
REGISTRATION_CLOSED_MESSAGE = (
    "由于作者个人财力有限，无法承担购买更多邮件通知服务的费用，"
    "本服务的当前用户数已达上限，已不再接收更多邮箱用户，诚挚感谢您的光临与理解！"
)

# 邮件退订链接签名盐，独立于其他 Django 签名用途。
UNSUBSCRIBE_TOKEN_SALT = "notice_app.unsubscribe"


# 返回当前项目中可展示给用户的去重板块名。
def get_section_names() -> list[str]:
    return [section.section_name for section in discover_sections()]


# 新用户默认不订阅任何板块，由用户进入设置页后自行勾选。
def get_default_preferences() -> list[str]:
    return []


# 获取或创建订阅用户，已注销用户重新登录时自动恢复。
def get_or_create_subscriber(email: str) -> Subscriber:
    # 统一邮箱格式，并用哈希作为查询键。
    normalized = normalize_email(email)
    subscriber, created = Subscriber.objects.get_or_create(
        email_hash=email_hash(normalized),
        defaults={
            "encrypted_email": encrypt_email(normalized),
            "preferences": get_default_preferences(),
            "known_sections": get_section_names(),
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


# 返回用户实际生效的订阅偏好，并记录用户已经见过的新增板块。
def get_effective_preferences(subscriber: Subscriber) -> list[str]:
    # 读取当前后端真实可订阅板块和用户历史已见板块。
    available = get_section_names()
    known = set(subscriber.known_sections or [])
    selected = set(subscriber.preferences or [])

    # 新增板块默认不勾选，只更新已见板块记录，等待用户自行选择。
    new_sections = [section for section in available if section not in known]
    effective_preferences = [section for section in available if section in selected]
    if new_sections or effective_preferences != list(subscriber.preferences or []):
        subscriber.preferences = effective_preferences
        subscriber.known_sections = available
        subscriber.save(update_fields=["preferences", "known_sections", "updated_at"])
    return effective_preferences


# 记录验证码请求并检查 IP 是否已被封禁或需要新加入黑名单。
def record_login_code_request(email: str, client_ip: str | None) -> tuple[bool, str]:
    # 规范化邮箱后仅保存哈希，避免请求日志中出现明文邮箱。
    normalized = normalize_email(email) if email else ""
    request_log = EmailVerificationRequest.objects.create(
        email_hash=email_hash(normalized) if normalized else "",
        client_ip=client_ip or None,
    )

    # 未启用 IP 黑名单时只记录请求，不执行封禁判断。
    if not config.ENABLE_LOGIN_IP_BLACKLIST:
        return True, ""

    # 已在黑名单中的 IP 直接拒绝后续验证码发送和登录校验。
    if is_login_code_ip_blacklisted(client_ip):
        request_log.was_blocked = True
        request_log.block_reason = "ip_blacklisted"
        request_log.save(update_fields=["was_blocked", "block_reason"])
        return False, "当前请求人数过多，请稍后"

    # 只有全局冷却期内才进行单 IP 高频审查，降低正常流量误伤。
    if not _is_email_smtp_global_cooling_down():
        return True, ""

    # 统计冷却期内该 IP 最近窗口的请求总量，包括已被拦截的请求。
    window_start = timezone.now() - timedelta(seconds=config.EMAIL_SMTP_IP_BAN_WINDOW_SECONDS)
    recent_request_count = EmailVerificationRequest.objects.filter(
        client_ip=client_ip or None,
        created_at__gte=window_start,
    ).count()
    if client_ip and recent_request_count > config.EMAIL_SMTP_IP_BAN_THRESHOLD:
        EmailVerificationIpBlacklist.objects.get_or_create(
            client_ip=client_ip,
            defaults={"reason": "login_code_request_rate_exceeded"},
        )
        request_log.was_blocked = True
        request_log.block_reason = "ip_rate_exceeded"
        request_log.save(update_fields=["was_blocked", "block_reason"])
        return False, "当前请求人数过多，请稍后"

    return True, ""


# 判断验证码请求 IP 是否处于黑名单。
def is_login_code_ip_blacklisted(client_ip: str | None) -> bool:
    if not config.ENABLE_LOGIN_IP_BLACKLIST:
        return False
    if not client_ip:
        return False
    return EmailVerificationIpBlacklist.objects.filter(client_ip=client_ip).exists()


# 判断当前邮箱是否允许继续注册或登录。
def can_accept_email_for_login(email: str) -> tuple[bool, str]:
    normalized = normalize_email(email)
    current_active_count = Subscriber.objects.filter(is_active=True).count()
    if current_active_count < config.REGISTRATION_USER_LIMIT:
        return True, ""

    # 已存在且仍激活的用户不占用新增名额，应允许继续登录维护偏好。
    existing_active = Subscriber.objects.filter(
        email_hash=email_hash(normalized),
        is_active=True,
    ).exists()
    if existing_active:
        return True, ""

    return False, REGISTRATION_CLOSED_MESSAGE


# 创建邮箱验证码记录并发送验证码邮件。
def request_login_code(email: str, client_ip: str | None = None) -> tuple[bool, str, int]:
    # 规范化邮箱并读取当前时间。
    normalized = normalize_email(email)
    now = timezone.now()

    # 用户数达到上限时，不再给新邮箱发送验证码。
    registration_allowed, registration_message = can_accept_email_for_login(normalized)
    if not registration_allowed:
        return False, registration_message, 0

    # 黑名单 IP 不允许继续触发验证码发送。
    if is_login_code_ip_blacklisted(client_ip):
        return False, "当前请求人数过多，请稍后", config.EMAIL_SMTP_GLOBAL_COOLDOWN_SECONDS

    # 登录验证码 SMTP 进入全局频限冷却时，不再继续消耗发件额度。
    allowed, cooldown_seconds = _check_email_smtp_global_rate_limit(now)
    if not allowed:
        return False, "当前请求人数过多，请稍后", cooldown_seconds

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
        client_ip=client_ip or None,
    )

    # 发送验证码邮件；SMTP 未配置时函数内部会安全跳过。
    _send_verification_email(normalized, code)
    return True, "验证码已发送，请留意邮箱。", int((verification.cooldown_until - now).total_seconds())


# 校验邮箱验证码，成功后返回订阅用户对象。
def verify_login_code(email: str, code: str) -> tuple[bool, str, Subscriber | None]:
    # 规范化邮箱并查找最新未使用验证码。
    normalized = normalize_email(email)
    now = timezone.now()

    # 用户数达到上限时，新邮箱不可继续创建或恢复账户。
    registration_allowed, registration_message = can_accept_email_for_login(normalized)
    if not registration_allowed:
        return False, registration_message, None

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


# 检查登录验证码 SMTP 是否超过全局发送频限。
def _check_email_smtp_global_rate_limit(now) -> tuple[bool, int]:
    state, _created = EmailSmtpRateLimitState.objects.get_or_create(
        name=EMAIL_SMTP_RATE_LIMIT_STATE_NAME,
    )

    # 冷却尚未结束时，直接拒绝新的验证码发送。
    if state.cooldown_until and state.cooldown_until > now:
        return False, max(1, int((state.cooldown_until - now).total_seconds()))

    # 统计最近一分钟真实发送的验证码数量。
    window_start = now - timedelta(seconds=60)
    sent_count = EmailVerification.objects.filter(created_at__gte=window_start).count()
    if sent_count < config.EMAIL_SMTP_MAX_SENDS_PER_MINUTE:
        return True, 0

    # 达到阈值后进入全局冷却期。
    state.cooldown_until = now + timedelta(seconds=config.EMAIL_SMTP_GLOBAL_COOLDOWN_SECONDS)
    state.save(update_fields=["cooldown_until", "updated_at"])
    return False, config.EMAIL_SMTP_GLOBAL_COOLDOWN_SECONDS


# 判断登录验证码 SMTP 是否处于全局冷却期。
def _is_email_smtp_global_cooling_down() -> bool:
    state = EmailSmtpRateLimitState.objects.filter(name=EMAIL_SMTP_RATE_LIMIT_STATE_NAME).first()
    return bool(state and state.cooldown_until and state.cooldown_until > timezone.now())


# 保存用户订阅偏好，只接受后端存在的板块名。
def update_preferences(subscriber: Subscriber, selected_sections: Sequence[str]) -> None:
    # 使用后端板块集合过滤前端提交值，防止非法 section 被写入数据库。
    available_sections = set(get_section_names())
    selected = [section for section in selected_sections if section in available_sections]
    subscriber.preferences = selected

    # 保存时记录当前已见板块，新增板块后仍默认不勾选。
    subscriber.known_sections = list(available_sections)
    subscriber.save(update_fields=["preferences", "known_sections", "updated_at"])


# 软注销订阅用户，停止后续邮件推送。
def deactivate_subscriber(subscriber: Subscriber) -> None:
    subscriber.is_active = False
    subscriber.preferences = []
    subscriber.save(update_fields=["is_active", "preferences", "updated_at"])


# 生成免登录退订令牌，用于通知邮件中的专属退订链接。
def build_unsubscribe_token(subscriber: Subscriber) -> str:
    payload = {"subscriber_id": subscriber.pk, "email_hash": subscriber.email_hash}
    return signing.dumps(payload, salt=UNSUBSCRIBE_TOKEN_SALT)


# 根据退订令牌软注销订阅用户，令牌无效时返回失败。
def unsubscribe_by_token(token: str) -> tuple[bool, str]:
    try:
        payload = signing.loads(token, salt=UNSUBSCRIBE_TOKEN_SALT)
    except signing.BadSignature:
        return False, "退订链接无效或已被修改。"
    if not isinstance(payload, dict):
        return False, "退订链接格式不正确。"

    subscriber_id = payload.get("subscriber_id")
    token_email_hash = payload.get("email_hash")
    subscriber = Subscriber.objects.filter(pk=subscriber_id, email_hash=token_email_hash).first()
    if subscriber is None:
        return False, "没有找到对应的邮箱订阅。"

    deactivate_subscriber(subscriber)
    return True, "退订成功。"


# 拼接完整退订链接，供后台邮件发送流程使用。
def build_unsubscribe_url(subscriber: Subscriber) -> str:
    base_url = str(config.SITE_BASE_URL).rstrip("/")
    token = quote(build_unsubscribe_token(subscriber), safe="")
    return f"{base_url}/unsubscribe/?token={token}"


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

    # 返回趋势点、当前激活用户数和新增邮箱上限。
    current_user_count = Subscriber.objects.filter(is_active=True).count()
    return {
        "points": points,
        "currentUserCount": current_user_count,
        "registrationUserLimit": config.REGISTRATION_USER_LIMIT,
        "registrationClosed": current_user_count >= config.REGISTRATION_USER_LIMIT,
    }


# 按 Web 用户订阅偏好和启用板块逐个过滤并发送本轮新增通知。
def dispatch_pending_notices(notices: Sequence[NoticeRecord]) -> MailDispatchSummary:
    summary = MailDispatchSummary()
    if not notices:
        return summary

    # 初始化邮件通知器，并读取当前激活订阅用户。
    notifier = EmailNotifier()
    active_subscribers = Subscriber.objects.filter(is_active=True)
    deliveries: list[tuple[str, list[NoticeRecord], str]] = []

    # 为每个用户解密邮箱并按其订阅板块过滤通知。
    for subscriber in active_subscribers:
        try:
            email = decrypt_email(subscriber.encrypted_email)
        except Exception as error:
            summary.failure_count += 1
            summary.failures.append(("<邮箱解密失败>", "邮箱解密失败"))
            logger.debug("订阅用户邮箱解密失败：subscriber_id=%s", subscriber.pk, exc_info=error)
            continue

        # 只发送用户勾选板块对应的新通知。
        selected_sections = get_effective_preferences(subscriber)
        target_notices = [notice for notice in notices if notice.section in selected_sections]
        if not target_notices:
            summary.success_count += 1
            continue

        deliveries.append((email, target_notices, build_unsubscribe_url(subscriber)))

    # 所有目标收件人共用一次 SMTP 会话发送，避免大量重复登录。
    failures = notifier.send_to_recipients(deliveries)
    failed_emails = {email for email, _reason in failures}
    summary.success_count += len(deliveries) - len(failed_emails)
    summary.failure_count += len(failures)
    summary.failures.extend(failures)

    return summary


# 将异常压缩为适合 INFO 级日志展示的短原因。
def _summarize_error(error: Exception) -> str:
    message = str(error).strip()
    if not message:
        return error.__class__.__name__
    return message[:120]


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
    message["Subject"] = "BJTU Campus News Radar 登录验证码"
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

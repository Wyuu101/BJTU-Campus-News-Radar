from __future__ import annotations

import ipaddress
import json
import re
import time

import config
from django.conf import settings
from django.http import FileResponse, Http404, HttpRequest, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from web.notice_app.crypto import decrypt_email
from web.notice_app.captcha_utils import create_captcha_payload, validate_captcha_answer
from web.notice_app.models import Subscriber
from web.notice_app.services import (
    can_accept_email_for_login,
    deactivate_subscriber,
    get_effective_preferences,
    get_public_stats,
    get_section_names,
    is_login_code_ip_blacklisted,
    record_login_code_request,
    request_login_code,
    unsubscribe_by_token,
    update_preferences,
    verify_login_code,
)


# 邮箱格式校验表达式，先做基础格式过滤，精细校验交给邮箱服务商。
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# 登录验证码校验接口的最小请求间隔，防止验证码爆破。
LOGIN_RATE_LIMIT_SECONDS = 1.0

# 基于进程内内存的 IP 限流记录；后续多进程部署可替换为 Redis。
_LOGIN_RATE_LIMIT_BY_IP: dict[str, float] = {}

# 基于进程内内存的图形验证码刷新限流记录；后续多进程部署可替换为 Redis。
_CAPTCHA_REFRESH_RATE_LIMIT_BY_IP: dict[str, float] = {}


# 渲染登录页；已登录用户也可返回首页查看展示内容或切换邮箱登录。
@ensure_csrf_cookie
def login_page(request: HttpRequest):
    return render(request, "notice_app/login.html")


# 返回站点 favicon，兼容浏览器默认请求的 /favicon.ico。
def favicon(request: HttpRequest):
    favicon_path = settings.WEB_DIR / "favicon.ico"
    if not favicon_path.exists():
        raise Http404("favicon.ico not found")
    return FileResponse(favicon_path.open("rb"), content_type="image/x-icon")


# 渲染个性化设置页；未登录用户回到登录页。
@ensure_csrf_cookie
def settings_page(request: HttpRequest):
    if _current_subscriber(request) is None:
        return redirect("/")
    return render(request, "notice_app/settings.html")


# 渲染打赏支持页。
def donate_page(request: HttpRequest):
    return render(request, "notice_app/donate.html")


# 渲染免登录退订确认页。
@ensure_csrf_cookie
def unsubscribe_page(request: HttpRequest):
    return render(request, "notice_app/unsubscribe.html", {"unsubscribe_token": request.GET.get("token", "")})


# 生成图形验证码图片信息。
@require_GET
def api_captcha(request: HttpRequest) -> JsonResponse:
    # 对用户主动刷新验证码做 1 秒限流，避免刷爆验证码图片生成。
    allowed, wait_seconds = _check_captcha_refresh_rate_limit(request)
    if not allowed:
        return JsonResponse(
            {"ok": False, "message": "操作太快，请稍后再换一张。", "retryAfter": wait_seconds},
            status=429,
        )

    # 生成并返回图片验证码 key 和图片 URL。
    captcha_payload = create_captcha_payload()
    return JsonResponse({"ok": True, "captcha": _captcha_payload_dict(captcha_payload)})


# 校验图形验证码并发送邮箱验证码。
@require_POST
def api_request_code(request: HttpRequest) -> JsonResponse:
    # 读取前端 JSON 请求体中的邮箱和图形验证码答案。
    payload = _json_payload(request)
    email = str(payload.get("email", "")).strip()
    captcha = str(payload.get("captcha", "")).strip()
    captcha_key = str(payload.get("captchaKey", "")).strip()

    # 邮箱格式不合法时提前拒绝，避免无意义发送。
    if not EMAIL_RE.match(email):
        return JsonResponse({"ok": False, "message": "邮箱格式有点不对。"}, status=400)

    # 达到人数上限时，新邮箱不再进入验证码发送流程。
    registration_allowed, registration_message = can_accept_email_for_login(email)
    if not registration_allowed:
        return JsonResponse({"ok": False, "message": registration_message}, status=429)

    # 记录本次验证码请求 IP，并在黑名单命中或冷却期高频请求时拒绝。
    client_ip = _client_ip(request)
    ip_allowed, ip_message = record_login_code_request(email, client_ip)
    if not ip_allowed:
        return JsonResponse({"ok": False, "message": ip_message}, status=429)

    # 图形验证码不匹配时拒绝发送，并直接返回下一张验证码。
    if not validate_captcha_answer(captcha_key, captcha):
        captcha_payload = create_captcha_payload()
        return JsonResponse(
            {
                "ok": False,
                "message": "图形验证码没有对上，请再试一次。",
                "captcha": _captcha_payload_dict(captcha_payload),
            },
            status=400,
        )

    # 调用服务层创建验证码记录并按冷却规则发送邮件。
    ok, message, cooldown = request_login_code(email, client_ip=client_ip)
    status = 200 if ok else 429
    return JsonResponse({"ok": ok, "message": message, "cooldown": cooldown}, status=status)


# 校验邮箱验证码并建立登录 session。
@require_POST
def api_login(request: HttpRequest) -> JsonResponse:
    # 对验证码校验接口做 1 秒限流，降低爆破风险。
    allowed, wait_seconds = _check_login_rate_limit(request)
    if not allowed:
        return JsonResponse(
            {"ok": False, "message": f"验证码校验太频繁了，请 {wait_seconds:.1f} 秒后再试。"},
            status=429,
        )

    # 黑名单 IP 不允许继续使用验证码登录接口。
    if is_login_code_ip_blacklisted(_client_ip(request)):
        return JsonResponse({"ok": False, "message": "当前请求人数过多，请稍后"}, status=429)

    # 读取邮箱和 8 位验证码。
    payload = _json_payload(request)
    email = str(payload.get("email", "")).strip()
    code = str(payload.get("code", "")).strip()

    # 基础参数校验失败时直接返回，不进入验证码匹配逻辑。
    if not EMAIL_RE.match(email) or not re.fullmatch(r"\d{8}", code):
        return JsonResponse({"ok": False, "message": "请输入邮箱和 8 位数字验证码。"}, status=400)

    # 达到人数上限时，新邮箱不再进入账户创建或恢复流程。
    registration_allowed, registration_message = can_accept_email_for_login(email)
    if not registration_allowed:
        return JsonResponse({"ok": False, "message": registration_message}, status=429)

    # 校验验证码，成功时自动创建或恢复订阅用户。
    ok, message, subscriber = verify_login_code(email, code)
    if not ok or subscriber is None:
        return JsonResponse({"ok": False, "message": message}, status=400)

    # 把订阅用户 ID 写入 session，后续短期免重复登录。
    request.session["subscriber_id"] = subscriber.id
    return JsonResponse({"ok": True, "message": message, "redirect": "/settings/"})


# 注销当前浏览器 session，但不注销订阅账户。
@require_POST
def api_logout(request: HttpRequest) -> JsonResponse:
    request.session.flush()
    return JsonResponse({"ok": True, "redirect": "/"})


# 返回当前登录用户信息和有效订阅偏好。
@require_GET
def api_me(request: HttpRequest) -> JsonResponse:
    # 未登录时返回 401，前端据此提示或跳转。
    subscriber = _current_subscriber(request)
    if subscriber is None:
        return JsonResponse({"ok": False, "message": "请先登录。"}, status=401)

    # 解密邮箱用于页面展示，偏好会自动补齐新增板块默认勾选。
    return JsonResponse(
        {
            "ok": True,
            "email": decrypt_email(subscriber.encrypted_email),
            "preferences": get_effective_preferences(subscriber),
            "dailyNotificationDisplayTime": config.DAILY_NOTIFICATION_DISPLAY_TIME,
        }
    )


# 返回后端自动发现的可订阅板块列表。
@require_GET
def api_sections(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"ok": True, "sections": get_section_names()})


# 保存当前登录用户的订阅偏好。
@require_POST
def api_preferences(request: HttpRequest) -> JsonResponse:
    # 只有登录用户可以保存偏好。
    subscriber = _current_subscriber(request)
    if subscriber is None:
        return JsonResponse({"ok": False, "message": "请先登录。"}, status=401)

    # 读取并校验前端提交的 section 列表。
    payload = _json_payload(request)
    sections = payload.get("sections", [])
    if not isinstance(sections, list):
        return JsonResponse({"ok": False, "message": "订阅设置格式不正确。"}, status=400)

    # 只保存后端认可的 section，防止前端篡改非法偏好。
    update_preferences(subscriber, [str(section) for section in sections])
    return JsonResponse({"ok": True, "message": "已保存，你的通知清单更新好了。"})


# 注销订阅账户并清空当前 session。
@require_http_methods(["DELETE"])
def api_delete_account(request: HttpRequest) -> JsonResponse:
    # 未登录时拒绝注销操作。
    subscriber = _current_subscriber(request)
    if subscriber is None:
        return JsonResponse({"ok": False, "message": "请先登录。"}, status=401)

    # 软注销用户，保留数据库记录但停止发送通知。
    deactivate_subscriber(subscriber)
    request.session.flush()
    return JsonResponse({"ok": True, "message": "账户已注销。", "redirect": "/"})


# 根据邮件退订令牌注销订阅账户。
@require_POST
def api_unsubscribe(request: HttpRequest) -> JsonResponse:
    payload = _json_payload(request)
    token = str(payload.get("token", "")).strip()
    if not token:
        return JsonResponse({"ok": False, "message": "退订链接缺少必要信息。"}, status=400)

    ok, message = unsubscribe_by_token(token)
    status = 200 if ok else 400
    return JsonResponse({"ok": ok, "message": message}, status=status)


# 返回首页公共统计数据。
@require_GET
def api_public_stats(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"ok": True, **get_public_stats()})


# 根据 session 中的 subscriber_id 读取当前登录用户。
def _current_subscriber(request: HttpRequest) -> Subscriber | None:
    subscriber_id = request.session.get("subscriber_id")
    if not subscriber_id:
        return None
    return Subscriber.objects.filter(id=subscriber_id, is_active=True).first()


# 解析 JSON 请求体，非法 JSON 时返回空字典。
def _json_payload(request: HttpRequest) -> dict[str, object]:
    if not request.body:
        return {}

    # JSON 解码失败时返回空参数，让上层统一走参数校验。
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


# 读取客户端 IP，优先支持反向代理传入的 X-Forwarded-For。
def _client_ip(request: HttpRequest) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return _validated_ip(forwarded.split(",")[0].strip())
    return _validated_ip(request.META.get("REMOTE_ADDR"))


# 校验并规范化客户端 IP，非法代理头直接忽略。
def _validated_ip(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return None


# 检查登录验证码校验接口是否触发 1 秒频率限制。
def _check_login_rate_limit(request: HttpRequest) -> tuple[bool, float]:
    # monotonic 时间不受系统时钟调整影响，更适合做短间隔限流。
    now = time.monotonic()
    client_key = _client_ip(request) or "unknown"
    session_key = "last_login_attempt_at"

    # 同时参考 session 和 IP 两个维度，降低刷新 session 绕过的概率。
    timestamps = [
        float(request.session.get(session_key, 0.0) or 0.0),
        _LOGIN_RATE_LIMIT_BY_IP.get(client_key, 0.0),
    ]

    # 未到最小间隔时返回剩余等待秒数。
    last_attempt = max(timestamps)
    elapsed = now - last_attempt
    if elapsed < LOGIN_RATE_LIMIT_SECONDS:
        return False, LOGIN_RATE_LIMIT_SECONDS - elapsed

    # 记录本次请求时间，供下一次请求判断。
    request.session[session_key] = now
    _LOGIN_RATE_LIMIT_BY_IP[client_key] = now
    return True, 0.0


# 检查图形验证码刷新接口是否触发频率限制。
def _check_captcha_refresh_rate_limit(request: HttpRequest) -> tuple[bool, float]:
    # monotonic 时间不受系统时间变更影响，适合短间隔限流。
    now = time.monotonic()
    client_key = _client_ip(request) or "unknown"
    session_key = "last_captcha_refresh_at"
    limit_seconds = float(settings.CAPTCHA_REFRESH_RATE_LIMIT_SECONDS)

    # 同时参考 session 和 IP 两个维度，降低刷新 session 绕过概率。
    timestamps = [
        float(request.session.get(session_key, 0.0) or 0.0),
        _CAPTCHA_REFRESH_RATE_LIMIT_BY_IP.get(client_key, 0.0),
    ]

    # 频率过高时返回剩余等待时间。
    last_refresh = max(timestamps)
    elapsed = now - last_refresh
    if elapsed < limit_seconds:
        return False, limit_seconds - elapsed

    # 记录本次刷新时间。
    request.session[session_key] = now
    _CAPTCHA_REFRESH_RATE_LIMIT_BY_IP[client_key] = now
    return True, 0.0


# 将 CaptchaPayload 转换为前端 JSON 字典。
def _captcha_payload_dict(captcha_payload) -> dict[str, str]:
    return {
        "key": captcha_payload.key,
        "imageUrl": captcha_payload.image_url,
    }

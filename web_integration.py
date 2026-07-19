from __future__ import annotations

import os
from typing import Sequence

from data_formats import QueuedNotice


# 初始化 Django 环境；未安装 Django 时允许 runner 继续走旧逻辑。
def setup_django() -> bool:
    # 延迟导入 Django，避免非 Web 环境执行 runner 时强依赖 Django。
    try:
        import django
    except ModuleNotFoundError:
        return False

    # 设置默认 settings 并完成 Django 应用初始化。
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.bjtu_notice_site.settings")
    django.setup()
    return True


# 将 runner 本轮新增通知数量写入 Web 每日统计表。
def record_new_notice_count(count: int) -> bool:
    if not setup_django():
        return False

    # 延迟导入服务函数，确保 Django setup 已完成。
    from web.notice_app.services import record_new_notice_count as record_count

    record_count(count)
    return True


# 使用 Web 用户订阅偏好发送通知；不可用时返回 None 让 runner 回退旧逻辑。
def dispatch_pending_notices(notices: Sequence[QueuedNotice]) -> bool | None:
    if not setup_django():
        return None

    # 延迟导入服务函数，确保模型已加载。
    from web.notice_app.services import dispatch_pending_notices as dispatch

    return dispatch(notices)

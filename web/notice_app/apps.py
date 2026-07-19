from __future__ import annotations

from django.apps import AppConfig


# Web 业务应用配置，供 Django 自动发现模型、静态资源和模板。
class NoticeAppConfig(AppConfig):
    # 默认使用 BigAutoField 作为模型主键类型。
    default_auto_field = "django.db.models.BigAutoField"

    # Django 应用导入路径。
    name = "web.notice_app"

    # Django 管理与调试输出中的应用显示名。
    verbose_name = "BJTU Notice Web"

from __future__ import annotations

from django.urls import path

from web.notice_app import views


# 站点 URL 路由表，页面路由和前端调用的 JSON API 都集中在这里。
urlpatterns = [
    path("", views.login_page, name="login_page"),
    path("settings/", views.settings_page, name="settings_page"),
    path("api/captcha/", views.api_captcha, name="api_captcha"),
    path("api/request-code/", views.api_request_code, name="api_request_code"),
    path("api/login/", views.api_login, name="api_login"),
    path("api/logout/", views.api_logout, name="api_logout"),
    path("api/me/", views.api_me, name="api_me"),
    path("api/sections/", views.api_sections, name="api_sections"),
    path("api/preferences/", views.api_preferences, name="api_preferences"),
    path("api/account/", views.api_delete_account, name="api_delete_account"),
    path("api/public-stats/", views.api_public_stats, name="api_public_stats"),
]

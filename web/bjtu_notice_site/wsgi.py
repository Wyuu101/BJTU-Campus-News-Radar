from __future__ import annotations

import os

from django.core.wsgi import get_wsgi_application


# 指定 WSGI 进程使用的默认 Django settings 模块。
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.bjtu_notice_site.settings")

# 暴露给 WSGI 服务器的应用对象。
application = get_wsgi_application()

from __future__ import annotations

import os
import sys


# 启动 Django 管理命令入口，例如 runserver、migrate、check。
def main() -> None:
    # 指定默认 Django settings 模块，允许命令行直接运行。
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.bjtu_notice_site.settings")

    # 延迟导入 Django 命令执行器，确保 settings 环境变量已设置。
    from django.core.management import execute_from_command_line

    # 将命令行参数交给 Django 处理。
    execute_from_command_line(sys.argv)


# 允许通过 python manage.py ... 直接执行管理命令。
if __name__ == "__main__":
    main()

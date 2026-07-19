from __future__ import annotations

import os
from pathlib import Path


# 解密导出当前激活订阅用户邮箱，便于本地运维核对。
def main() -> int:
    # 设置 Django settings，允许脚本直接从项目根目录执行。
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.bjtu_notice_site.settings")

    # 初始化 Django 应用和 ORM。
    import django

    django.setup()

    # 延迟导入模型和解密函数，确保 Django 初始化完成。
    from web.notice_app.crypto import decrypt_email
    from web.notice_app.models import Subscriber

    # 导出文件放在 data 目录，避免进入源码目录。
    output_path = Path("data") / "subscriber_emails.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 只导出仍处于激活状态的订阅用户。
    emails: list[str] = []
    for subscriber in Subscriber.objects.filter(is_active=True).order_by("id"):
        emails.append(decrypt_email(subscriber.encrypted_email))

    # 写入 UTF-8 文本，每行一个邮箱。
    output_path.write_text("\n".join(emails), encoding="utf-8")
    print(f"已导出 {len(emails)} 个邮箱到 {output_path}")
    return 0


# 允许通过 python scripts/export_subscriber_emails.py 直接执行。
if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import html
import smtplib
from collections import defaultdict
from email.message import EmailMessage
from smtplib import SMTP, SMTP_SSL
from typing import Sequence

import config
from app_logging import get_runner_logger
from data_formats import NoticeRecord


logger = get_runner_logger("runner.email")

EMAIL_WIDTH_PX = 640


class EmailNotifier:
    """邮件通知器。

    未配置 SMTP 时不发送邮件，由 runner 记录失败并返回非零退出码。
    """

    # 根据 SMTP 配置判断邮件通知器是否可用。
    def __init__(self) -> None:
        self.enabled = bool(
            config.SMTP_HOST
            and config.SMTP_FROM
            and config.SMTP_USERNAME
            and config.SMTP_PASSWORD
        )

    # 发送给单个 Web 订阅用户，供个性化偏好过滤后调用。
    def send_to_recipient(
        self,
        recipient: str,
        notices: Sequence[NoticeRecord],
    ) -> bool:
        if not notices:
            return True

        if not self.enabled:
            logger.debug("SMTP 未配置，无法发送给 %s 的 %s 条通知。", recipient, len(notices))
            return False

        if config.SMTP_USE_SSL:
            with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT) as smtp:
                smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
                self._send_message_to_recipient(smtp, recipient, notices)
        else:
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as smtp:
                smtp.starttls()
                smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
                self._send_message_to_recipient(smtp, recipient, notices)

        return True

    # 发送 runner 异常报告给管理员邮箱。
    def send_admin_report(
        self,
        *,
        scan_success_count: int,
        scan_failure_count: int,
        scan_failures: Sequence[str],
        mail_success_count: int,
        mail_failure_count: int,
        mail_failures: Sequence[tuple[str, str]],
    ) -> bool:
        if not config.ADMIN_EMAIL:
            logger.warning("管理员邮箱未配置，异常报告未发送。")
            return False

        if not self.enabled:
            logger.warning("SMTP 未配置，异常报告未发送。")
            return False

        message = self._build_admin_report_message(
            recipient=config.ADMIN_EMAIL,
            scan_success_count=scan_success_count,
            scan_failure_count=scan_failure_count,
            scan_failures=scan_failures,
            mail_success_count=mail_success_count,
            mail_failure_count=mail_failure_count,
            mail_failures=mail_failures,
        )

        if config.SMTP_USE_SSL:
            with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT) as smtp:
                smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
                smtp.send_message(message, from_addr=config.SMTP_FROM, to_addrs=[config.ADMIN_EMAIL])
        else:
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as smtp:
                smtp.starttls()
                smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
                smtp.send_message(message, from_addr=config.SMTP_FROM, to_addrs=[config.ADMIN_EMAIL])
        return True

    # 构造发给单个收件人的邮件对象，避免暴露其他收件人地址。
    def _build_message(
        self,
        recipient: str,
        notices: Sequence[NoticeRecord],
    ) -> EmailMessage:
        message = EmailMessage()
        message["Subject"] = f"叮咚~已为您捕捉到 {len(notices)} 条新通知"
        message["From"] = config.SMTP_FROM
        message["To"] = recipient
        message.set_content(self._build_plain_text_body(notices))
        message.add_alternative(
            self._build_html_body(notices),
            subtype="html",
        )
        return message

    # 构造管理员异常报告邮件对象。
    def _build_admin_report_message(
        self,
        *,
        recipient: str,
        scan_success_count: int,
        scan_failure_count: int,
        scan_failures: Sequence[str],
        mail_success_count: int,
        mail_failure_count: int,
        mail_failures: Sequence[tuple[str, str]],
    ) -> EmailMessage:
        message = EmailMessage()
        message["Subject"] = "BJTU Campus News Radar 异常报告"
        message["From"] = config.SMTP_FROM
        message["To"] = recipient
        message.set_content(
            self._build_admin_report_text(
                scan_success_count=scan_success_count,
                scan_failure_count=scan_failure_count,
                scan_failures=scan_failures,
                mail_success_count=mail_success_count,
                mail_failure_count=mail_failure_count,
                mail_failures=mail_failures,
            )
        )
        message.add_alternative(
            self._build_admin_report_html(
                scan_success_count=scan_success_count,
                scan_failure_count=scan_failure_count,
                scan_failures=scan_failures,
                mail_success_count=mail_success_count,
                mail_failure_count=mail_failure_count,
                mail_failures=mail_failures,
            ),
            subtype="html",
        )
        return message

    # 将一封只包含单个收件人的邮件发送给指定邮箱。
    def _send_message_to_recipient(
        self,
        smtp: SMTP | SMTP_SSL,
        recipient: str,
        notices: Sequence[NoticeRecord],
    ) -> None:
        message = self._build_message(recipient, notices)
        smtp.send_message(message, from_addr=config.SMTP_FROM, to_addrs=[recipient])

    # 构造纯文本邮件正文。
    def _build_plain_text_body(
        self,
        notices: Sequence[NoticeRecord],
    ) -> str:
        notices_by_section = self._group_notices_by_section(notices)
        lines = [f"叮咚~已为您捕捉到 {len(notices)} 条新通知：", ""]
        for section, section_notices in notices_by_section.items():
            lines.append(f"[{section}]")
            for index, notice in enumerate(section_notices, start=1):
                lines.extend(
                    [
                        f"   {index}. {notice.title}",
                        f"      日期：{notice.date or '未知'}",
                        f"      来源：北京交通大学{self._source_name(notice.section)}官网",
                        f"      链接：{notice.url}",
                    ]
                )
            lines.append("")
        return "\n".join(lines)

    # 构造管理员异常报告纯文本正文。
    def _build_admin_report_text(
        self,
        *,
        scan_success_count: int,
        scan_failure_count: int,
        scan_failures: Sequence[str],
        mail_success_count: int,
        mail_failure_count: int,
        mail_failures: Sequence[tuple[str, str]],
    ) -> str:
        lines = [
            "BJTU Campus News Radar 异常报告",
            "",
            f"雷达扫描：{scan_success_count} 成功，{scan_failure_count} 异常。",
        ]
        lines.extend(f"- {item}" for item in scan_failures)
        lines.extend(["", f"邮件通知：{mail_success_count} 成功，{mail_failure_count} 异常。"])
        lines.extend(f"- {email}: {reason}" for email, reason in mail_failures)
        return "\n".join(lines)

    # 构造 HTML 邮件正文。
    def _build_html_body(
        self,
        notices: Sequence[NoticeRecord],
    ) -> str:
        notices_by_section = self._group_notices_by_section(notices)
        section_blocks = "\n".join(
            self._build_section_block(section, section_notices)
            for section, section_notices in notices_by_section.items()
        )
        notice_count = len(notices)
        section_count = len(notices_by_section)
        title = self._escape(f"叮咚~已为您捕捉到 {notice_count} 条新通知")
        subtitle = self._escape(
            f"我把它们按 {section_count} 个板块分好类了，泡杯咖啡慢慢看也不迟。"
        )

        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="x-apple-disable-message-reformatting">
  <style>
    @media screen and (max-width: 680px) {{
      .email-shell {{ width: 100% !important; }}
      .email-container {{ padding: 18px 12px !important; }}
      .hero-card {{ padding: 24px 20px !important; }}
      .notice-card {{ padding: 20px !important; }}
      .section-panel {{ padding: 20px !important; }}
      .email-title {{ font-size: 24px !important; line-height: 1.25 !important; }}
      .notice-title {{ font-size: 16px !important; line-height: 1.45 !important; }}
      .button-link {{ display: block !important; text-align: center !important; }}
      .copy-link {{ display: block !important; text-align: center !important; margin:10px 0 0 !important; }}
    }}
  </style>
</head>
<body style="margin:0;padding:0;background:#eef5ff;background-image:linear-gradient(135deg,#eaf2ff 0%,#fff8f1 42%,#f2f0ff 72%,#ecfbf7 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;color:#172033;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">
    叮咚~本轮为您捕捉到 {notice_count} 条新通知。
  </div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="width:100%;border-collapse:collapse;background:#eef5ff;background-image:radial-gradient(circle at 12% 8%,rgba(99,102,241,0.16) 0,rgba(99,102,241,0) 28%),radial-gradient(circle at 85% 18%,rgba(20,184,166,0.14) 0,rgba(20,184,166,0) 26%),linear-gradient(135deg,#eaf2ff 0%,#fff8f1 42%,#f2f0ff 72%,#ecfbf7 100%);">
    <tr>
      <td class="email-container" align="center" style="padding:36px 16px;">
        <table role="presentation" class="email-shell" width="{EMAIL_WIDTH_PX}" cellspacing="0" cellpadding="0" border="0" style="width:{EMAIL_WIDTH_PX}px;max-width:{EMAIL_WIDTH_PX}px;border-collapse:separate;border-spacing:0;">
          <tr>
            <td class="hero-card" style="padding:30px 32px;border-radius:18px;background:rgba(255,255,255,0.84);background-image:linear-gradient(135deg,rgba(255,255,255,0.94),rgba(246,250,255,0.74));box-shadow:0 22px 58px rgba(31,45,61,0.14);border:1px solid rgba(255,255,255,0.82);">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border-collapse:collapse;">
                <tr>
                  <td style="width:44px;vertical-align:top;">
                    <div style="width:36px;height:36px;border-radius:12px;background:#e8f0ff;background-image:linear-gradient(135deg,#dbeafe,#f5d0fe);color:#315fbd;text-align:center;line-height:36px;font-size:18px;">📬</div>
                  </td>
                  <td style="vertical-align:top;">
                    <h1 class="email-title" style="margin:0;font-size:28px;line-height:1.2;font-weight:700;letter-spacing:0;color:#101828;">{title}</h1>
                    <p style="margin:10px 0 0;font-size:14px;line-height:1.7;color:#667085;">{subtitle}</p>
                  </td>
                </tr>
              </table>
              <div style="height:1px;background:linear-gradient(90deg,#c7d2fe,#99f6e4,rgba(219,230,244,0));margin:24px 0 2px;border-radius:12px;"></div>
            </td>
          </tr>
          <tr>
            <td style="height:18px;font-size:1px;line-height:18px;">&nbsp;</td>
          </tr>
          {section_blocks}
          <tr>
            <td style="padding:22px 10px 0;text-align:center;color:#98a2b3;font-size:12px;line-height:1.7;">
              <div style="border-top:1px solid rgba(152,162,179,0.22);padding-top:18px;">
                此邮件由 BJTU Campus News Radar 自动发送。请勿直接回复。
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    # 构造管理员异常报告 HTML 正文。
    def _build_admin_report_html(
        self,
        *,
        scan_success_count: int,
        scan_failure_count: int,
        scan_failures: Sequence[str],
        mail_success_count: int,
        mail_failure_count: int,
        mail_failures: Sequence[tuple[str, str]],
    ) -> str:
        scan_items = self._build_admin_report_items(scan_failures)
        mail_items = self._build_admin_report_items(
            [f"{email}: {reason}" for email, reason in mail_failures]
        )
        return f"""<!doctype html>
<html lang="zh-CN">
<body style="margin:0;padding:0;background:#f7f3ee;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;color:#292524;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="padding:34px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="{EMAIL_WIDTH_PX}" cellspacing="0" cellpadding="0" border="0" style="max-width:{EMAIL_WIDTH_PX}px;width:100%;border-collapse:separate;border-spacing:0;">
          <tr>
            <td style="padding:28px;border-radius:22px;background:#fffaf5;border:1px solid #eadfd3;box-shadow:0 22px 52px rgba(120,94,70,.14);">
              <h1 style="margin:0;font-size:24px;line-height:1.3;color:#2f261f;">BJTU Campus News Radar 异常报告</h1>
              <p style="margin:10px 0 0;color:#7b6d61;font-size:14px;line-height:1.7;">本轮运行检测到异常，请及时查看。</p>
            </td>
          </tr>
          <tr><td style="height:16px;font-size:1px;line-height:16px;">&nbsp;</td></tr>
          <tr>
            <td style="padding:24px;border-radius:18px;background:#fffaf5;border:1px solid #eadfd3;">
              <h2 style="margin:0 0 12px;font-size:18px;color:#2f261f;">爬虫异常情况</h2>
              <p style="margin:0 0 14px;color:#7b6d61;">扫描完毕，{scan_success_count}成功，{scan_failure_count}异常。</p>
              {scan_items}
            </td>
          </tr>
          <tr><td style="height:16px;font-size:1px;line-height:16px;">&nbsp;</td></tr>
          <tr>
            <td style="padding:24px;border-radius:18px;background:#fffaf5;border:1px solid #eadfd3;">
              <h2 style="margin:0 0 12px;font-size:18px;color:#2f261f;">邮件异常情况</h2>
              <p style="margin:0 0 14px;color:#7b6d61;">邮件通知任务完成，成功{mail_success_count}，异常{mail_failure_count}</p>
              {mail_items}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    # 构造管理员报告中的异常条目列表。
    def _build_admin_report_items(self, items: Sequence[str]) -> str:
        if not items:
            return '<p style="margin:0;color:#8a7a6b;font-size:14px;">无异常。</p>'
        content = "".join(
            f'<li style="margin:0 0 8px;color:#7a4f2d;font-size:14px;line-height:1.6;">{self._escape(item)}</li>'
            for item in items
        )
        return f'<ul style="margin:0;padding-left:20px;">{content}</ul>'

    # 按板块分组通知。
    def _group_notices_by_section(
        self,
        notices: Sequence[NoticeRecord],
    ) -> dict[str, list[NoticeRecord]]:
        grouped: dict[str, list[NoticeRecord]] = defaultdict(list)
        for notice in notices:
            grouped[notice.section].append(notice)
        return dict(grouped)

    # 构造一个板块分组及其中的通知卡片。
    def _build_section_block(
        self,
        section: str,
        notices: Sequence[NoticeRecord],
    ) -> str:
        section_text = self._escape(section)
        count_text = self._escape(f"{len(notices)} 条新消息")
        content = "\n".join(
            self._build_notice_card(notice, index)
            for index, notice in enumerate(notices, start=1)
        )

        return f"""<tr>
            <td class="section-panel" style="padding:24px 26px;border-radius:16px;background:rgba(255,255,255,0.72);background-image:linear-gradient(145deg,rgba(255,255,255,0.88),rgba(239,246,255,0.66));box-shadow:0 12px 34px rgba(31,45,61,0.08);border:1px solid rgba(255,255,255,0.78);">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border-collapse:collapse;">
                <tr>
                  <td style="padding-bottom:16px;">
                    <div style="font-size:12px;line-height:1.2;color:#98a2b3;margin-bottom:7px;">SECTION</div>
                    <h2 style="margin:0;color:#101828;font-size:20px;line-height:1.35;font-weight:700;">{section_text}</h2>
                  </td>
                  <td align="right" style="padding-bottom:16px;vertical-align:top;">
                    <span style="display:inline-block;padding:6px 10px;border-radius:999px;background:#eef4ff;background-image:linear-gradient(135deg,#e0f2fe,#ede9fe);color:#315fbd;font-size:12px;font-weight:700;">{count_text}</span>
                  </td>
                </tr>
              </table>
              {content}
            </td>
          </tr>
          <tr>
            <td style="height:16px;font-size:1px;line-height:16px;">&nbsp;</td>
          </tr>"""

    # 构造单条通知的 HTML 卡片。
    def _build_notice_card(self, notice: NoticeRecord, index: int) -> str:
        title = self._escape(notice.title)
        section = self._escape(notice.section)
        date = self._escape(notice.date or "日期未知")
        url = self._escape(notice.url)
        source = self._escape(f"来源：北京交通大学{self._source_name(notice.section)}官网")

        return f"""<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border-collapse:collapse;margin-top:12px;">
            <tr>
            <td class="notice-card" style="padding:22px;border-radius:14px;background:rgba(255,255,255,0.92);background-image:linear-gradient(160deg,rgba(255,255,255,0.96),rgba(248,250,252,0.88));box-shadow:0 8px 24px rgba(31,45,61,0.08);border:1px solid rgba(226,232,240,0.88);">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border-collapse:collapse;">
                <tr>
                  <td style="padding:0 0 12px;">
                    <span style="display:inline-block;padding:5px 10px;border-radius:999px;background:#f2f5f9;color:#667085;font-size:12px;line-height:1.2;">{section}</span>
                    <span style="display:inline-block;margin-left:8px;color:#98a2b3;font-size:12px;line-height:1.2;">{date}</span>
                  </td>
                </tr>
                <tr>
                  <td>
                    <h2 class="notice-title" style="margin:0;color:#172033;font-size:18px;line-height:1.5;font-weight:700;letter-spacing:0;">{index}. {title}</h2>
                  </td>
                </tr>
                <tr>
                  <td style="padding-top:18px;">
                    <a class="button-link" href="{url}" target="_blank" style="display:inline-block;min-width:96px;padding:11px 18px;border-radius:12px;background:#315fbd;background-image:linear-gradient(135deg,#315fbd,#5b6ee1);color:#ffffff;text-decoration:none;font-size:14px;font-weight:600;text-align:center;box-shadow:0 8px 18px rgba(49,95,189,0.22);">查看通知</a>
                    <div style="margin-top:14px;color:#98a2b3;font-size:12px;line-height:1.6;">{source}</div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          </table>"""

    # 转义 HTML 文本，避免标题或链接中的特殊字符破坏邮件结构。
    def _escape(self, value: str) -> str:
        return html.escape(value, quote=True)

    # 从“来源-板块”形式的 section 中提取官网来源名。
    def _source_name(self, section: str) -> str:
        return section.split("-", 1)[0].strip() or section.strip()

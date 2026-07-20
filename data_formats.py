from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResultSummary:
    """Source Adapter 返回给 Runner 的统一通知摘要格式。"""

    # 内容所属板块，例如“电信学院-学院动态”
    section: str
    # 内容标题
    title: str
    # 内容详情链接
    url: str
    # 内容发布日期；不同网站格式可能不同，先保留原始字符串
    date: str | None = None


@dataclass(frozen=True, slots=True)
class NoticeRecord:
    """已入库且可用于邮件通知的通知记录。"""

    notice_id: int
    section: str
    title: str
    url: str
    date: str | None
    content_hash: str

from __future__ import annotations

import hashlib
import re
from urllib.parse import urldefrag

from data_formats import ResultSummary


_WHITESPACE_RE = re.compile(r"\s+")


# 规整文本中的空白字符，便于入库和比对。
def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return _WHITESPACE_RE.sub(" ", value).strip()


# 规整 URL，去掉不会影响详情页身份的 fragment。
def normalize_url(url: str) -> str:
    # 去掉 URL fragment，避免同一详情页因为锚点不同被误判为新通知。
    normalized, _fragment = urldefrag(url.strip())
    return normalized


# 根据通知摘要生成稳定 SHA256 指纹。
def build_notice_hash(notice: ResultSummary, section_id: str = "") -> str:
    """生成稳定指纹，用于 SQLite 去重。

    优先依赖 URL；同时加入 section_id/section/title，避免不同脚本或异常 URL 时冲突。
    """

    payload = "\n".join(
        (
            normalize_text(section_id),
            normalize_text(notice.section),
            normalize_text(notice.title),
            normalize_url(notice.url),
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

import config
from data_formats import QueuedNotice, ResultSummary
from utils import build_notice_hash, normalize_text, normalize_url


class NoticeStore:
    """SQLite 持久化层：负责建表、去重、待发送队列。"""

    # 初始化存储对象并确保数据库目录存在。
    def __init__(self, db_path: Path = config.DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    # 初始化 SQLite 表结构和必要索引。
    def initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode = WAL;

                CREATE TABLE IF NOT EXISTS notices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_hash TEXT NOT NULL UNIQUE,
                    section TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    date TEXT,
                    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS email_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    notice_id INTEGER NOT NULL UNIQUE,
                    status TEXT NOT NULL DEFAULT 'queued',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    sent_at TEXT,
                    last_error TEXT,
                    FOREIGN KEY (notice_id) REFERENCES notices(id)
                );

                CREATE INDEX IF NOT EXISTS idx_email_queue_status
                ON email_queue(status, created_at);
                """
            )

    # 写入抓取结果，过滤旧通知，并把新增通知加入邮件队列。
    def add_notices(self, notices: Iterable[ResultSummary]) -> list[QueuedNotice]:
        """写入本次抓取结果，并返回新增且已进入邮件队列的通知。"""

        queued: list[QueuedNotice] = []
        with self._connect() as conn:
            for notice in notices:
                notice_hash = build_notice_hash(notice)
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO notices
                        (content_hash, section, title, url, date)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        notice_hash,
                        normalize_text(notice.section),
                        normalize_text(notice.title),
                        normalize_url(notice.url),
                        normalize_text(notice.date),
                    ),
                )

                if cursor.rowcount == 0:
                    continue

                notice_id = int(cursor.lastrowid)
                queue_cursor = conn.execute(
                    "INSERT INTO email_queue (notice_id) VALUES (?)",
                    (notice_id,),
                )
                queued.append(
                    QueuedNotice(
                        queue_id=int(queue_cursor.lastrowid),
                        notice_id=notice_id,
                        section=notice.section,
                        title=notice.title,
                        url=notice.url,
                        date=notice.date,
                        content_hash=notice_hash,
                    )
                )
        return queued

    # 读取当前仍未成功发送的邮件队列。
    def get_pending_queue(self, limit: int | None = None) -> list[QueuedNotice]:
        sql = """
            SELECT
                q.id AS queue_id,
                n.id AS notice_id,
                n.section,
                n.title,
                n.url,
                n.date,
                n.content_hash
            FROM email_queue q
            JOIN notices n ON n.id = q.notice_id
            WHERE q.status = 'queued'
            ORDER BY q.created_at ASC, q.id ASC
        """
        params: tuple[int, ...] = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (limit,)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [
            QueuedNotice(
                queue_id=int(row["queue_id"]),
                notice_id=int(row["notice_id"]),
                section=row["section"],
                title=row["title"],
                url=row["url"],
                date=row["date"],
                content_hash=row["content_hash"],
            )
            for row in rows
        ]

    # 将指定队列项标记为已发送。
    def mark_sent(self, queue_ids: Iterable[int]) -> None:
        ids = list(queue_ids)
        if not ids:
            return
        placeholders = ",".join("?" for _ in ids)
        with self._connect() as conn:
            conn.execute(
                f"""
                UPDATE email_queue
                SET status = 'sent', sent_at = CURRENT_TIMESTAMP, last_error = NULL
                WHERE id IN ({placeholders})
                """,
                ids,
            )

    # 记录发送失败原因，并保留队列项供下次重试。
    def mark_failed(self, queue_ids: Iterable[int], error: str) -> None:
        ids = list(queue_ids)
        if not ids:
            return
        placeholders = ",".join("?" for _ in ids)
        with self._connect() as conn:
            conn.execute(
                f"""
                UPDATE email_queue
                SET status = 'queued', last_error = ?
                WHERE id IN ({placeholders})
                """,
                (error, *ids),
            )

    # 创建 SQLite 连接并启用按列名读取结果。
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

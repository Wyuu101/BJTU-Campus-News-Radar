from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

import config
from data_formats import NoticeRecord, ResultSummary
from utils import build_notice_hash, normalize_text, normalize_url


class NoticeStore:
    """SQLite 持久化层：负责建表和通知去重。"""

    # 初始化存储对象并确保数据库目录存在。
    def __init__(self, db_path: Path = config.DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    # 判断数据库文件是否已经存在，用于 runner 区分首次初始化部署。
    def exists(self) -> bool:
        return self.db_path.exists()

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

                DROP TABLE IF EXISTS email_queue;
                """
            )

    # 写入扫描结果，过滤旧通知，并返回本轮新增通知。
    def add_notices(self, notices: Iterable[ResultSummary]) -> list[NoticeRecord]:
        """写入本次扫描结果，并返回本轮首次发现的通知。"""

        new_records: list[NoticeRecord] = []
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
                new_records.append(
                    NoticeRecord(
                        notice_id=notice_id,
                        section=normalize_text(notice.section),
                        title=normalize_text(notice.title),
                        url=normalize_url(notice.url),
                        date=normalize_text(notice.date),
                        content_hash=notice_hash,
                    )
                )
        return new_records

    # 读取当前数据库中已经出现过的板块名，用于判断新增爬虫板块是否需要初始化。
    def get_existing_sections(self) -> set[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT DISTINCT section FROM notices").fetchall()
        return {normalize_text(row["section"]) for row in rows if row["section"]}

    # 创建 SQLite 连接并启用按列名读取结果。
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

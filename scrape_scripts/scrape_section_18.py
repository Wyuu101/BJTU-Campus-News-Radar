from __future__ import annotations

import time
import random
from typing import Any
from urllib.parse import urljoin

import requests

import config
from app_logging import get_source_logger
from data_formats import ResultSummary


logger = get_source_logger(__name__)

SECTION_ID = "section_18"
SECTION_NAME = "就业资讯-双选会"

BASE_URL = "https://job.bjtu.edu.cn/f/bilateralchosefair/ajax_frontBilateralchosefair"
SITE_ROOT_URL = "https://job.bjtu.edu.cn/"



MAX_PAGES = 1

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Host": "job.bjtu.edu.cn",
    "Referer": "https://job.bjtu.edu.cn/frontpage/bjtu/html/bilateralchosefairList.html?type=4",
    "X-Requested-With": "XMLHttpRequest",
}


# 请求并解析当前板块的单个分页。
def parse_page(
    session: requests.Session,
    page: int,
) -> list[ResultSummary] | None:
    """解析指定页。

    返回 None 表示请求或响应结构异常；返回空列表表示没有更多数据。
    """

     # URL 查询字符串参数
    query_params = {
        "ts": 1784623813427,
    }


    try:
        response = session.get(
            BASE_URL,
            params=query_params,
            timeout=config.REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as error:
        logger.debug("第 %s 页请求异常：%s", page, error)
        return None

    if response.status_code != 200:
        logger.debug("第 %s 页请求失败，HTTP 状态码：%s", page, response.status_code)
        return None

    try:
        response_data = response.json()
    except requests.exceptions.JSONDecodeError as error:
        logger.debug("第 %s 页响应不是合法 JSON：%s", page, error)
        return None

    if not isinstance(response_data, dict):
        logger.debug("第 %s 页 JSON 顶层结构不是对象。", page)
        return None

    dic_v1 = response_data.get("object")
    if dic_v1 is None : return None
    item_list = dic_v1.get("list")
    if not isinstance(item_list, list):
        logger.debug("第 %s 页 JSON 中未找到有效的 List 字段。", page)
        return None

    results: list[ResultSummary] = []
    for item in item_list:
        result = _parse_list_item(item)
        if result is not None:
            results.append(result)

    logger.debug(
        "第 %s 页解析完成，总记录数：%s，本页获取到 %s 条通知。",
        page,
        response_data.get("Count", "未知"),
        len(results),
    )
    return results


# 当前板块的独立扫描入口，内部可自由决定是否翻页。
def crawl(max_pages: int = MAX_PAGES) -> list[ResultSummary] | None:
    """连续扫描前 max_pages 页，供 runner 调用。"""

    all_results: list[ResultSummary] = []

    with requests.Session() as session:
        session.headers.update(HEADERS)

        for page in range(1, max_pages + 1):
            page_results = parse_page(session=session, page=page)
            if page_results is None:
                logger.debug("扫描中止：第 %s 页失败。", page)
                return None

            if not page_results:
                logger.debug("第 %s 页没有数据，停止翻页。", page)
                break

            all_results.extend(page_results)

            if config.REQUEST_DELAY_SECONDS > 0:
                time.sleep(config.REQUEST_DELAY_SECONDS)

    unique_results = {result.url: result for result in all_results}
    logger.debug("板块 %s 完成去重：%s 条。", SECTION_ID, len(unique_results))
    return list(unique_results.values())


# 从接口返回的单条 JSON 数据中提取统一通知摘要。
def _parse_list_item(item: Any) -> ResultSummary | None:
    if not isinstance(item, dict):
        return None

    title = item.get("title")
    date = ""
    href = item.get("url")

    if not isinstance(title, str) or not title.strip():
        return None

    if not isinstance(href, str) or not href.strip():
        return None

    if not isinstance(date, str) or not date.strip():
        date = None

    return ResultSummary(
        section=SECTION_NAME,
        title=title.strip(),
        url=urljoin(SITE_ROOT_URL, href.strip()),
        date=date.strip() if date is not None else None,
    )


# 允许本脚本单独运行，用于调试当前板块。
def main() -> None:
    from scrape_scripts.debug_runner import run_standalone

    run_standalone(globals())


if __name__ == "__main__":
    main()

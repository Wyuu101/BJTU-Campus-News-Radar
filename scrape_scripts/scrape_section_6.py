from __future__ import annotations

import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import config
from app_logging import get_source_logger
from data_formats import ResultSummary


logger = get_source_logger(__name__)

SECTION_ID = "section_6"
SECTION_NAME = "校史馆-动态信息"

BASE_URL = "https://archives.bjtu.edu.cn/dtxx/"

MAX_PAGES = 1

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}


# 请求并解析当前板块的单个分页。
def parse_page(
    session: requests.Session,
    page: int,
) -> list[ResultSummary] | None:
    """解析指定页。

    返回 None 表示请求或页面结构异常；返回空列表表示没有更多数据。
    """

    try:
        response = session.get(
            BASE_URL,
            timeout=config.REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as error:
        logger.debug("第 %s 页请求异常：%s", page, error)
        return None

    if response.status_code != 200:
        logger.debug("第 %s 页请求失败，HTTP 状态码：%s", page, response.status_code)
        return None

    # 部分中文站点会被 requests 误判为 iso-8859-1。
    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding

    soup = BeautifulSoup(response.text, "html.parser")
    news_list = soup.find_all("table", class_="w12")[4].find("tbody")
    if news_list is None:
        logger.debug("第 %s 页未找到 table.w12[4]", page)
        return []
    results: list[ResultSummary] = []
    count = 0
    for item in news_list.find_all("tr", recursive=False):
        if count==0 : 
            count = count + 1
            continue
        result = _parse_list_item(item, response.url)
        if result is not None:
            results.append(result)
        count = count + 1

    logger.debug("第 %s 页解析完成，获取到 %s 条。", page, len(results))
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


# 从列表页的单个 li 节点中提取统一通知摘要。
def _parse_list_item(item: BeautifulSoup, base_url: str) -> ResultSummary | None:

    content = item.find("td")

    if content is None:
        return None

    title_and_href_node = content.find("a", href=True)
    if title_and_href_node is None:
        return None

    title = title_and_href_node.get_text(" ", strip=True)
    href = title_and_href_node.get("href")
    if not title or not isinstance(href, str):
        return None

    return ResultSummary(
        section=SECTION_NAME,
        title=title,
        url=urljoin(base_url, href),
        date=_parse_date(item),
    )


# 从列表项日期节点中解析发布时间文本。
def _parse_date(item: BeautifulSoup) -> str | None:
    date_node = item.find_all("td")[1]
    if date_node is None:
        return None
    date_node_div = date_node.find("div")
    if date_node_div is None:
        return None
    date_node_div_font = date_node_div.find("font")

    date = date_node_div_font.get_text(strip=True) if date_node_div_font is not None else None
    return f"{date}" if date else None


# 允许本脚本单独运行，用于调试当前板块。
def main() -> None:
    from scrape_scripts.debug_runner import run_standalone

    run_standalone(globals())


if __name__ == "__main__":
    main()

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import requests

from app_logging import setup_logging
from data_formats import ResultSummary


# 单独运行爬虫脚本时的通用调试入口，不影响 runner 调用 crawl() 的生产逻辑。
def run_standalone(module_globals: dict[str, Any]) -> None:
    setup_logging(source_debug=True)

    # 从调用脚本的全局变量中读取既有配置和函数，避免每个爬虫重复实现调试逻辑。
    logger = module_globals["logger"]
    logger.disabled = False
    parse_page: Callable[..., list[ResultSummary] | None] = module_globals["parse_page"]
    config = module_globals["config"]
    headers = module_globals.get("HEADERS", {})
    max_pages = int(module_globals.get("MAX_PAGES", 1))
    section_id = str(module_globals.get("SECTION_ID", "unknown_section"))
    section_name = str(module_globals.get("SECTION_NAME", section_id))

    all_results: list[ResultSummary] = []
    logger.info("手动调试开始：%s（%s），计划扫描 %s 页。", section_name, section_id, max_pages)

    with requests.Session() as session:
        session.headers.update(headers)

        for page in range(1, max_pages + 1):
            logger.info("开始扫描第 %s 页。", page)
            page_results = parse_page(session=session, page=page)

            if page_results is None:
                logger.error("第 %s 页扫描失败，本次手动调试中止。", page)
                break

            logger.info("第 %s 页扫描完成，本页获取 %s 条。", page, len(page_results))
            _log_result_list(logger, page_results, prefix=f"第 {page} 页")

            if not page_results:
                logger.info("第 %s 页没有数据，停止继续翻页。", page)
                break

            all_results.extend(page_results)

            if config.REQUEST_DELAY_SECONDS > 0:
                time.sleep(config.REQUEST_DELAY_SECONDS)

    unique_results = list({result.url: result for result in all_results}.values())
    logger.info(
        "全部页面扫描完毕：累计获取 %s 条，按 URL 去重后剩余 %s 条。",
        len(all_results),
        len(unique_results),
    )
    _log_result_list(logger, unique_results, prefix="最终结果")


# 输出标题、URL 与日期明细，便于单独调试爬虫时核对解析质量。
def _log_result_list(logger: Any, results: list[ResultSummary], *, prefix: str) -> None:
    if not results:
        logger.info("%s明细：无。", prefix)
        return

    logger.info("%s标题、URL 与日期列表：", prefix)
    for index, result in enumerate(results, start=1):
        logger.info("%s. %s | %s | %s", index, result.title, result.url, result.date or "未知")

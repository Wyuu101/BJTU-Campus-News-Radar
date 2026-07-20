from __future__ import annotations

import importlib
from collections.abc import Callable

import config
from app_logging import get_runner_logger, setup_logging
from data_formats import ResultSummary
from storage import NoticeStore
from web_integration import dispatch_pending_notices, record_new_notice_count


logger = get_runner_logger("runner")


SourceCrawler = Callable[[], list[ResultSummary] | None]


# 从配置中加载各网页板块的入口函数。
def load_crawlers() -> list[tuple[str, SourceCrawler]]:
    crawlers: list[tuple[str, SourceCrawler]] = []
    for module_name, function_name in config.SOURCE_ADAPTERS:
        module = importlib.import_module(module_name)
        crawl = getattr(module, function_name, None)
        if not callable(crawl):
            raise TypeError(f"{module_name} 必须暴露可调用的 {function_name}() 函数")
        crawlers.append((f"{module_name}.{function_name}", crawl))
    return crawlers


# 执行一轮完整监控任务：抓取、入库去重、按 Web 用户偏好发送邮件。
def run_once() -> int:
    setup_logging()

    store = NoticeStore()
    is_initial_deploy = not store.exists()
    store.initialize()

    crawlers = load_crawlers()
    logger.info("监控任务启动：%s 个网页板块。", len(crawlers))

    all_new_count = 0
    all_new_records = []
    for module_name, crawl in crawlers:
        logger.info("开始抓取：%s", module_name)
        try:
            results = crawl()
        except Exception:
            logger.exception("抓取失败：%s", module_name)
            continue

        if results is None:
            logger.warning("抓取中止：%s", module_name)
            continue

        new_records = store.add_notices(results)
        all_new_count += len(new_records)
        all_new_records.extend(new_records)
        logger.info(
            "抓取完成：%s，本次获取 %s 条，新增 %s 条。",
            module_name,
            len(results),
            len(new_records),
        )

    if is_initial_deploy:
        logger.info("检测到首次初始化部署：已入库 %s 条通知，本轮不发送邮件。", all_new_count)
        return 0

    if not all_new_records:
        logger.info("本轮没有新增通知，无需发送邮件。")
        return 0

    try:
        record_new_notice_count(all_new_count)
    except Exception as error:
        logger.exception("新增通知统计写入失败：%s", error)
        return 1

    try:
        sent = dispatch_pending_notices(all_new_records)
    except Exception:
        logger.exception("邮件发送失败。")
        return 1

    if not sent:
        logger.error("邮件发送未完成，请检查 SMTP 配置或用户邮箱数据。")
        return 1

    logger.info("监控任务结束：本轮新增 %s 条。", all_new_count)
    return 0


if __name__ == "__main__":
    raise SystemExit(run_once())

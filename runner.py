from __future__ import annotations

import importlib
from collections.abc import Callable

import config
from app_logging import get_runner_logger, setup_logging
from data_formats import ResultSummary
from email_notifier import EmailNotifier
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


# 执行一轮完整雷达扫描：扫描、入库去重、按 Web 用户偏好发送邮件。
def run_once() -> int:
    setup_logging()
    logger.info("=" * 72)

    store = NoticeStore()
    is_initial_deploy = not store.exists()
    store.initialize()

    crawlers = load_crawlers()
    logger.info("雷达扫描启动：%s 个网页板块。", len(crawlers))

    all_new_count = 0
    all_new_records = []
    scan_success_count = 0
    scan_failure_count = 0
    scan_failures: list[str] = []
    for module_name, crawl in crawlers:
        logger.info("开始扫描：%s", module_name)
        try:
            results = crawl()
        except Exception as error:
            scan_failure_count += 1
            scan_failures.append(f"{module_name}: {_summarize_error(error)}")
            logger.exception("扫描失败：%s", module_name)
            continue

        if results is None:
            scan_failure_count += 1
            scan_failures.append(f"{module_name}: 返回结果为空")
            logger.warning("扫描中止：%s", module_name)
            continue

        new_records = store.add_notices(results)
        all_new_count += len(new_records)
        all_new_records.extend(new_records)
        if len(results) == 0:
            scan_failure_count += 1
            scan_failures.append(f"{module_name}: 本次获取 0 条")
        else:
            scan_success_count += 1
        logger.info(
            "扫描完成：%s，本次获取 %s 条，新增 %s 条。",
            module_name,
            len(results),
            len(new_records),
        )

    logger.info("扫描完毕，%s成功，%s异常。", scan_success_count, scan_failure_count)

    mail_success_count = 0
    mail_failure_count = 0
    mail_failures: list[tuple[str, str]] = []
    if is_initial_deploy:
        logger.info("检测到首次初始化部署：已入库 %s 条通知，本轮不写入今日统计，也不发送邮件。", all_new_count)
    else:
        if not all_new_records:
            logger.info("本轮没有新增通知，无需发送邮件。")
        else:
            try:
                stats_recorded = record_new_notice_count(all_new_count)
            except Exception as error:
                mail_failure_count += 1
                mail_failures.append(("<统计写入>", _summarize_error(error)))
                logger.exception("新增通知统计写入失败：%s", error)
            else:
                if not stats_recorded:
                    mail_failure_count += 1
                    mail_failures.append(("<统计写入>", "Web 环境不可用"))
                else:
                    try:
                        mail_summary = dispatch_pending_notices(all_new_records)
                    except Exception as error:
                        mail_failure_count += 1
                        mail_failures.append(("<邮件任务>", _summarize_error(error)))
                        logger.exception("邮件发送失败。")
                    else:
                        if mail_summary is None:
                            mail_failure_count += 1
                            mail_failures.append(("<邮件任务>", "Web 环境不可用"))
                        else:
                            mail_success_count = mail_summary.success_count
                            mail_failure_count = mail_summary.failure_count
                            mail_failures = mail_summary.failures
                logger.info("邮件通知任务完成，成功%s，异常%s", mail_success_count, mail_failure_count)
                if mail_failures:
                    for email, reason in mail_failures:
                        logger.info("%s：%s", email, reason)

        if scan_failure_count or mail_failure_count:
            _report_runner_abnormalities(
                scan_success_count=scan_success_count,
                scan_failure_count=scan_failure_count,
                scan_failures=scan_failures,
                mail_success_count=mail_success_count,
                mail_failure_count=mail_failure_count,
                mail_failures=mail_failures,
            )

    logger.info("雷达扫描结束：本轮新增 %s 条。", all_new_count)
    return 1 if scan_failure_count or mail_failure_count else 0


# 将异常压缩为适合 INFO 级日志展示的短原因。
def _summarize_error(error: Exception) -> str:
    message = str(error).strip()
    if not message:
        return error.__class__.__name__
    return message[:120]


# 异常存在时发送管理员报告，报告发送失败不再触发二次上报。
def _report_runner_abnormalities(
    *,
    scan_success_count: int,
    scan_failure_count: int,
    scan_failures: list[str],
    mail_success_count: int,
    mail_failure_count: int,
    mail_failures: list[tuple[str, str]],
) -> None:
    try:
        sent = EmailNotifier().send_admin_report(
            scan_success_count=scan_success_count,
            scan_failure_count=scan_failure_count,
            scan_failures=scan_failures,
            mail_success_count=mail_success_count,
            mail_failure_count=mail_failure_count,
            mail_failures=mail_failures,
        )
    except Exception as error:
        logger.exception("异常报告发送失败：%s", error)
        return

    if sent:
        logger.info("已上报异常")


if __name__ == "__main__":
    raise SystemExit(run_once())

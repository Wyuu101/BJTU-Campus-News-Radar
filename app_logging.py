from __future__ import annotations

import logging
import sys

import config


SOURCE_LOGGER_PREFIXES = ("scrape_section_", "sources.")


# 配置全局日志输出规则。
def setup_logging(
    *,
    runner_level: str | int = config.RUNNER_LOG_LEVEL,
    source_debug: bool = config.DEBUG_SOURCES,
) -> None:
    """配置全局日志。

    默认只允许 runner 输出进度信息；各网页适配器日志只有在 DEBUG_SOURCES 开启时输出。
    """

    root = logging.getLogger()
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if source_debug else runner_level)

    logging.getLogger("runner").setLevel(runner_level)
    _set_source_loggers_enabled(source_debug)


# 获取 Runner 使用的日志器。
def get_runner_logger(name: str = "runner") -> logging.Logger:
    return logging.getLogger(name)


# 获取网页板块脚本使用的日志器。
def get_source_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.disabled = not config.DEBUG_SOURCES
    logger.setLevel(logging.DEBUG)
    return logger


# 根据全局开关启用或禁用各网页板块脚本的日志输出。
def _set_source_loggers_enabled(enabled: bool) -> None:
    manager = logging.Logger.manager
    for logger_name, logger_obj in manager.loggerDict.items():
        if not isinstance(logger_obj, logging.Logger):
            continue
        if logger_name.startswith(SOURCE_LOGGER_PREFIXES):
            logger_obj.disabled = not enabled
            logger_obj.setLevel(logging.DEBUG)

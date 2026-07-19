from __future__ import annotations

import importlib
import importlib.util
from dataclasses import dataclass

import config


# 爬虫板块描述，用于前端订阅列表自动展示。
@dataclass(frozen=True, slots=True)
class SourceSection:
    # 爬虫模块名，例如 scrape_section_01。
    module_name: str

    # 爬虫暴露的 SECTION_NAME，用于用户订阅和邮件过滤。
    section_name: str


# 自动发现当前配置中已启用的可订阅板块。
def discover_sections() -> list[SourceSection]:
    """Discover unique section names from enabled scrape modules."""

    # 只读取 config.SOURCE_ADAPTERS 中启用的模块，未启用脚本不会展示到前端。
    module_names = _candidate_module_names()

    # 用 section_name 去重，避免不同脚本展示重复板块选项。
    sections: dict[str, SourceSection] = {}
    for module_name in module_names:
        # 某个模块导入失败时跳过，避免一个坏适配器阻断整个订阅列表。
        try:
            module = importlib.import_module(module_name)
        except Exception:
            continue

        # 只接受定义了非空 SECTION_NAME 的爬虫模块。
        section_name = getattr(module, "SECTION_NAME", None)
        if not isinstance(section_name, str) or not section_name.strip():
            continue

        # 保留第一次出现的模块，确保展示顺序稳定。
        clean_name = section_name.strip()
        sections.setdefault(clean_name, SourceSection(module_name=module_name, section_name=clean_name))
    return list(sections.values())


# 收集所有候选爬虫模块名，并保持顺序去重。
def _candidate_module_names() -> list[str]:
    # 读取配置中启用的爬虫模块，保持 runner 的业务顺序。
    names: list[str] = []
    for module_name, _function_name in getattr(config, "SOURCE_ADAPTERS", []):
        if importlib.util.find_spec(module_name) is not None:
            names.append(module_name)

    # 顺序去重，避免同一模块被配置和扫描重复加入。
    seen: set[str] = set()
    unique_names: list[str] = []
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        unique_names.append(name)
    return unique_names

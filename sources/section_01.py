# 兼容 sources 包导入方式，实际逻辑仍在独立脚本 scrap_section_01.py。
from scrap_section_01 import crawl
from scrap_section_15 import crawl

__all__ = ["crawl"]

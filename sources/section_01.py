# 兼容 sources 包导入方式，实际逻辑仍在独立脚本 scrape_section_01.py。
from scrape_section_01 import crawl

__all__ = ["crawl"]

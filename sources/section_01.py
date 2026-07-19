# 兼容 sources 包导入方式，实际逻辑仍在 scrape_scripts.scrape_section_01。
from scrape_scripts.scrape_section_01 import crawl

__all__ = ["crawl"]

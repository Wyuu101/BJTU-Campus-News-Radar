"""网页板块 Source Adapter 包。

后续新增板块时，建议复制 section_01 的接口形态：
crawl() -> list[ResultSummary] | None。
每个板块内部可以自行决定是否分页、是否请求多个页面或接口。
"""

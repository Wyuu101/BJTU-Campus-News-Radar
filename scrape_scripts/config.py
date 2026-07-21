from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


# 项目根目录，真实 config.py 位于这里。
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 真实配置文件路径，供直接运行 scrape_section_*.py 时代理加载。
PROJECT_CONFIG_PATH = PROJECT_ROOT / "config.py"

# 将项目根目录加入模块搜索路径，保证 app_logging、data_formats 等顶层模块可导入。
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 通过文件路径加载根目录 config.py，避免再次导入当前兼容层造成递归。
spec = importlib.util.spec_from_file_location("_project_config", PROJECT_CONFIG_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"Cannot load project config from {PROJECT_CONFIG_PATH}")

# 执行真实配置模块，并把其中的配置项透传到当前模块命名空间。
project_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(project_config)

# 只暴露真实 config.py 中的公开名称，保持 import config 的使用方式不变。
for name in dir(project_config):
    if not name.startswith("__"):
        globals()[name] = getattr(project_config, name)

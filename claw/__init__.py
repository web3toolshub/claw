"""
claw - OpenClaw 配置管理工具包

用于管理 openclaw 配置的工具包。

当前提供的功能：
- 优化 ~/.openclaw/openclaw.json
"""

__version__ = "0.1.4"
__author__ = "YLX Studio"

from .main import (  # noqa: F401
    CONFIG_PATH,
    OPENCLAW_COMMAND,
    TARGET_ID,
    TOOL_PROFILE,
    ensure_allow_from,
    ensure_tools_profile,
    load_config,
    main,
    restart_gateway,
    save_config,
    update_config,
)

__all__ = [
    "CONFIG_PATH",
    "OPENCLAW_COMMAND",
    "TARGET_ID",
    "TOOL_PROFILE",
    "ensure_allow_from",
    "ensure_tools_profile",
    "load_config",
    "main",
    "restart_gateway",
    "save_config",
    "update_config",
]

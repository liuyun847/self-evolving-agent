"""core/shell_tools.py - 命令行工具模块

提供 shell 命令执行功能，封装 subprocess 调用并格式化输出。
"""

from __future__ import annotations

import os
import subprocess


def run_command(
    command: str,
    timeout: int = 30,
    env: dict[str, str] | None = None,
) -> str:
    """执行命令行命令并返回格式化结果

    Args:
        command: 要执行的 shell 命令字符串
        timeout: 超时时间（秒），默认 30
        env: 额外的环境变量字典，会合并到当前进程环境中

    Returns:
        格式化字符串，包含退出码、stdout 和 stderr

    Raises:
        subprocess.TimeoutExpired: 命令执行超时
    """
    merged_env: dict[str, str] = os.environ.copy()
    if env:
        merged_env.update(env)

    result: subprocess.CompletedProcess[str] = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=merged_env,
    )

    return (
        f"退出码: {result.returncode}\n"
        f"--- stdout ---\n"
        f"{result.stdout}"
        f"--- stderr ---\n"
        f"{result.stderr}"
    )
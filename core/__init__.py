"""core - 核心工具集包

提供工具注册表和所有基础工具模块。core/ 为只读锚点，不可被 Agent 修改。
"""

from typing import Any

from core.file_tools import (
    APPEND_FILE_PARAMETERS,
    DELETE_FILE_PARAMETERS,
    LIST_DIR_PARAMETERS,
    READ_FILE_PARAMETERS,
    WRITE_FILE_PARAMETERS,
    append_file,
    delete_file,
    list_dir,
    read_file,
    write_file,
)
from core.git_tools import git_add, git_commit, git_diff, git_log, git_reset, git_status
from core.inbox_listener import InboxListener
from core.registry import ToolRegistry, ToolSpec
from core.shell_tools import run_command
from core.web_tools import web_fetch, web_search

# ---------------------------------------------------------------------------
# 参数 Schema 常量（shell / web / git 工具）
# ---------------------------------------------------------------------------

RUN_COMMAND_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "command": {
            "type": "string",
            "description": "要执行的 shell 命令",
        },
        "timeout": {
            "type": "integer",
            "description": "超时时间（秒），默认 30",
        },
        "env": {
            "type": "object",
            "description": "额外的环境变量字典（可选）",
        },
    },
    "required": ["command"],
}

WEB_SEARCH_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "搜索关键词",
        },
        "num_results": {
            "type": "integer",
            "description": "返回结果数量上限，默认 5",
        },
    },
    "required": ["query"],
}

WEB_FETCH_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "url": {
            "type": "string",
            "description": "目标网页 URL",
        },
        "timeout": {
            "type": "integer",
            "description": "请求超时秒数，默认 30",
        },
    },
    "required": ["url"],
}

GIT_STATUS_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "required": [],
}

GIT_ADD_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "paths": {
            "type": "string",
            "description": "要添加的文件路径，空格分隔多个，默认 '.'",
        },
    },
    "required": [],
}

GIT_COMMIT_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "message": {
            "type": "string",
            "description": "提交信息",
        },
    },
    "required": ["message"],
}

GIT_DIFF_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "required": [],
}

GIT_LOG_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "n": {
            "type": "integer",
            "description": "返回的日志条数，默认 10",
        },
    },
    "required": [],
}

GIT_RESET_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "hard": {
            "type": "boolean",
            "description": "是否硬重置（丢弃工作区修改），默认 False（soft）",
        },
    },
    "required": [],
}


def create_default_registry() -> ToolRegistry:
    """创建并返回预注册了所有基础工具的注册表实例"""
    registry = ToolRegistry()

    # 文件工具
    registry.register(
        "read_file", "读取文件内容", READ_FILE_PARAMETERS, read_file
    )
    registry.register(
        "write_file", "写入文件（覆盖已有内容）", WRITE_FILE_PARAMETERS, write_file
    )
    registry.register(
        "append_file", "追加内容到文件末尾", APPEND_FILE_PARAMETERS, append_file
    )
    registry.register(
        "list_dir", "列出目录内容", LIST_DIR_PARAMETERS, list_dir
    )
    registry.register(
        "delete_file", "删除文件", DELETE_FILE_PARAMETERS, delete_file
    )

    # 命令行工具
    registry.register(
        "run_command", "执行 shell 命令并返回结果", RUN_COMMAND_PARAMETERS, run_command
    )

    # 网页工具
    registry.register(
        "web_search", "搜索网页（DuckDuckGo）", WEB_SEARCH_PARAMETERS, web_search
    )
    registry.register(
        "web_fetch", "捕获网页内容为纯文本", WEB_FETCH_PARAMETERS, web_fetch
    )

    # Git 工具
    registry.register(
        "git_status", "查看 git 状态", GIT_STATUS_PARAMETERS, git_status
    )
    registry.register(
        "git_add", "添加文件到暂存区", GIT_ADD_PARAMETERS, git_add
    )
    registry.register(
        "git_commit", "提交暂存的变更", GIT_COMMIT_PARAMETERS, git_commit
    )
    registry.register(
        "git_diff", "查看工作区差异", GIT_DIFF_PARAMETERS, git_diff
    )
    registry.register(
        "git_log", "查看提交历史", GIT_LOG_PARAMETERS, git_log
    )
    registry.register(
        "git_reset", "重置 git（默认 soft HEAD~1，hard 则 --hard HEAD）",
        GIT_RESET_PARAMETERS, git_reset
    )

    return registry


__all__ = [
    "ToolRegistry",
    "ToolSpec",
    "InboxListener",
    "create_default_registry",
    # 文件工具
    "read_file",
    "write_file",
    "append_file",
    "list_dir",
    "delete_file",
    # 命令行工具
    "run_command",
    # 网页工具
    "web_search",
    "web_fetch",
    # Git 工具
    "git_status",
    "git_add",
    "git_commit",
    "git_diff",
    "git_log",
    "git_reset",
]
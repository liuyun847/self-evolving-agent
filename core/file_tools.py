"""core/file_tools.py - 文件工具模块

提供文件与目录操作的纯函数，供 ToolRegistry 注册为 LLM 可调用的工具。
每个函数独立无副作用（除文件系统写入），返回值均为字符串，方便 LLM 消费。
"""

from pathlib import Path
from typing import Any


def read_file(path: str) -> str:
    """读取文件全部内容

    Args:
        path: 文件路径（字符串形式）

    Returns:
        文件完整内容（UTF-8 解码后的字符串）

    Raises:
        FileNotFoundError: 文件不存在
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"文件不存在: {path}")
    return file_path.read_text(encoding="utf-8")


def write_file(path: str, content: str) -> str:
    """写入文件（覆盖已有内容）

    Args:
        path: 文件路径（字符串形式）
        content: 要写入的内容

    Returns:
        操作成功消息

    Raises:
        IsADirectoryError: path 指向一个已存在的目录
    """
    file_path = Path(path)
    if file_path.is_dir():
        raise IsADirectoryError(f"路径是目录，无法写入文件: {path}")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return f"文件已写入: {path}"


def append_file(path: str, content: str) -> str:
    """追加内容到文件末尾

    Args:
        path: 文件路径（字符串形式）
        content: 要追加的内容

    Returns:
        操作成功消息

    Raises:
        FileNotFoundError: 文件不存在
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"文件不存在，无法追加: {path}")
    with file_path.open("a", encoding="utf-8") as f:
        f.write(content)
    return f"内容已追加到: {path}"


def list_dir(path: str) -> str:
    """列出目录内容

    每行一个条目，目录以 '/' 结尾。

    Args:
        path: 目录路径（字符串形式）

    Returns:
        目录内容列表，每行一个条目

    Raises:
        FileNotFoundError: 目录不存在
        NotADirectoryError: 路径不是目录
    """
    dir_path = Path(path)
    if not dir_path.exists():
        raise FileNotFoundError(f"目录不存在: {path}")
    if not dir_path.is_dir():
        raise NotADirectoryError(f"路径不是目录: {path}")
    entries: list[str] = []
    for entry in sorted(dir_path.iterdir()):
        name = entry.name
        if entry.is_dir():
            name += "/"
        entries.append(name)
    return "\n".join(entries) if entries else "(空目录)"


def delete_file(path: str) -> str:
    """删除文件

    Args:
        path: 文件路径（字符串形式）

    Returns:
        操作成功消息

    Raises:
        FileNotFoundError: 文件不存在
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"文件不存在: {path}")
    file_path.unlink()
    return f"文件已删除: {path}"


# ---------------------------------------------------------------------------
# 各工具的 JSON Schema 参数定义（OpenAI function calling 格式）
# 供 ToolRegistry.register() 使用，不在此文件中注册
# ---------------------------------------------------------------------------

READ_FILE_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "要读取的文件路径",
        },
    },
    "required": ["path"],
}

WRITE_FILE_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "要写入的文件路径",
        },
        "content": {
            "type": "string",
            "description": "要写入的内容",
        },
    },
    "required": ["path", "content"],
}

APPEND_FILE_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "要追加内容的文件路径",
        },
        "content": {
            "type": "string",
            "description": "要追加的内容",
        },
    },
    "required": ["path", "content"],
}

LIST_DIR_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "要列出内容的目录路径",
        },
    },
    "required": ["path"],
}

DELETE_FILE_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "要删除的文件路径",
        },
    },
    "required": ["path"],
}
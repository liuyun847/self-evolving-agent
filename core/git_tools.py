"""core/git_tools.py - Git 工具模块

提供模块级函数，封装常用 git 命令，通过 subprocess.run 调用。
所有 git 命令在项目根目录（/workspace）执行。
"""

import os
import subprocess

_PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""项目根目录（core/ 的上一级目录，基于文件位置动态计算）"""


def _run_git(args: list[str], timeout: int = 30) -> str:
    """执行 git 命令并返回输出，出错时返回 stderr

    Args:
        args: git 命令参数列表，不含 "git" 前缀
        timeout: 超时时间（秒），默认 30

    Returns:
        命令的 stdout（成功时）或 stderr（失败时）
    """
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            cwd=_PROJECT_ROOT,
            timeout=timeout,
        )
    except FileNotFoundError:
        return "错误: git 命令不可用，请确认 git 已安装并在 PATH 中"
    except subprocess.TimeoutExpired:
        return f"错误: git 命令执行超时（{timeout}秒）"
    except PermissionError as exc:
        return f"错误: 权限不足: {exc}"
    except OSError as exc:
        return f"错误: 系统错误: {exc}"

    if result.returncode != 0:
        return result.stderr.strip()
    return result.stdout.strip()


def git_status() -> str:
    """执行 git status --porcelain，返回状态输出"""
    return _run_git(["status", "--porcelain"])


def git_add(paths: str = ".") -> str:
    """执行 git add <paths>，paths 支持空格分隔的多个路径

    Args:
        paths: 要添加的文件路径，空格分隔多个路径，默认为 "."

    Returns:
        stdout 或 stderr
    """
    return _run_git(["add", *paths.split()])


def git_commit(message: str) -> str:
    """执行 git commit -m <message>

    Args:
        message: 提交信息

    Returns:
        stdout 或 stderr
    """
    return _run_git(["commit", "-m", message])


def git_diff() -> str:
    """执行 git diff HEAD，返回差异"""
    return _run_git(["diff", "HEAD"])


def git_log(n: int = 10) -> str:
    """执行 git log --oneline -n <n>，返回日志

    Args:
        n: 返回的日志条数，默认 10

    Returns:
        日志输出
    """
    return _run_git(["log", "--oneline", f"-n{n}"])


def git_reset(hard: bool = False) -> str:
    """执行 git reset，hard=True 时 --hard HEAD，否则 --soft HEAD~1

    Args:
        hard: 是否执行硬重置（丢弃工作区修改）

    Returns:
        stdout 或 stderr
    """
    if hard:
        return _run_git(["reset", "--hard", "HEAD"])
    return _run_git(["reset", "--soft", "HEAD~1"])
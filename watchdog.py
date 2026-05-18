"""看门狗模块 - 监控 agent.py 进程存活，保证系统最低可用性。

检测到 agent 进程死亡时，执行 git reset --hard HEAD 后重新启动。
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time
from typing import NoReturn

logger = logging.getLogger("watchdog")
"""看门狗日志记录器"""

_CHECK_INTERVAL: float = 3.0
"""检测间隔（秒）"""

_AGENT_SCRIPT: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent.py")
"""agent.py 的绝对路径"""

_shutdown_flag: bool = False
"""优雅退出标志，信号处理函数设置此标志"""


def _setup_logging() -> None:
    """配置日志格式与级别。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


def _signal_handler(signum: int, _frame: object) -> None:
    """SIGTERM / SIGINT 信号处理函数，设置退出标志。

    Args:
        signum: 信号编号
        _frame: 当前栈帧（未使用）
    """
    global _shutdown_flag
    sig_name = signal.Signals(signum).name
    logger.info("收到 %s 信号，准备优雅退出", sig_name)
    _shutdown_flag = True


def _register_signals() -> None:
    """注册 SIGTERM 和 SIGINT 信号处理函数。"""
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
    logger.info("已注册 SIGTERM/SIGINT 信号处理")


def _start_agent() -> subprocess.Popen[bytes] | None:
    """使用 subprocess.Popen 启动 agent.py 子进程。

    传递当前进程的所有环境变量。

    Returns:
        Popen 对象，若 agent.py 不存在则返回 None
    """
    if not os.path.isfile(_AGENT_SCRIPT):
        logger.error("agent.py 未找到: %s", _AGENT_SCRIPT)
        return None

    logger.info("正在启动 agent.py ...")
    try:
        proc = subprocess.Popen(
            [sys.executable, _AGENT_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
            cwd=os.path.dirname(_AGENT_SCRIPT),
        )
        logger.info("agent.py 已启动，PID=%d", proc.pid)
        return proc
    except OSError as exc:
        logger.exception("启动 agent.py 失败: %s", exc)
        return None


def _is_alive(pid: int) -> bool:
    """通过 os.kill(pid, 0) 检测进程是否存活。

    Args:
        pid: 进程 ID

    Returns:
        进程存活返回 True，否则返回 False
    """
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _terminate_agent(proc: subprocess.Popen[bytes]) -> None:
    """优雅终止 agent 子进程。

    先发送 SIGTERM，等待最多 5 秒后若未退出则 SIGKILL。

    Args:
        proc: agent 子进程的 Popen 对象
    """
    pid = proc.pid
    if pid is None:
        return

    logger.info("正在终止 agent 子进程 (PID=%d) ...", pid)

    try:
        proc.terminate()
    except OSError:
        pass

    try:
        proc.wait(timeout=5.0)
        logger.info("agent 子进程已正常退出")
    except subprocess.TimeoutExpired:
        logger.warning("agent 子进程未响应 SIGTERM，发送 SIGKILL")
        try:
            proc.kill()
            proc.wait()
            logger.info("agent 子进程已被强制终止")
        except OSError:
            pass


def _git_reset_hard() -> bool:
    """执行 git reset --hard HEAD 回滚所有未提交变更。

    Returns:
        执行成功返回 True，否则返回 False
    """
    cwd = os.path.dirname(_AGENT_SCRIPT)
    logger.info("执行 git reset --hard HEAD ...")

    try:
        result = subprocess.run(
            ["git", "reset", "--hard", "HEAD"],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=30,
        )
        if result.returncode == 0:
            logger.info("git reset 成功:\n%s", result.stdout.strip())
            return True
        else:
            logger.error("git reset 失败 (rc=%d):\n%s", result.returncode, result.stderr.strip())
            return False
    except FileNotFoundError:
        logger.exception("git 命令不可用")
        return False
    except subprocess.TimeoutExpired:
        logger.exception("git reset 超时")
        return False


def main() -> NoReturn:
    """看门狗主函数。

    启动 agent.py 子进程，每 _CHECK_INTERVAL 秒检测其存活状态。
    若进程死亡，执行 git reset --hard HEAD 后重新启动。
    收到 SIGTERM/SIGINT 后优雅退出。
    """
    global _shutdown_flag

    _setup_logging()
    logger.info("看门狗启动")

    _register_signals()

    proc: subprocess.Popen[bytes] | None = _start_agent()

    while not _shutdown_flag:
        time.sleep(_CHECK_INTERVAL)

        if _shutdown_flag:
            break

        if proc is None:
            # 首次启动失败，尝试重新启动
            logger.warning("agent 进程未启动，尝试重新启动")
            proc = _start_agent()
            continue

        pid = proc.pid
        if pid is None:
            logger.warning("无法获取 agent PID，重新启动")
            proc = _start_agent()
            continue

        if _is_alive(pid):
            logger.debug("agent (PID=%d) 存活", pid)
            continue

        logger.warning("agent (PID=%d) 已死亡，执行恢复流程", pid)

        # 收集子进程输出（非阻塞）
        try:
            stdout, stderr = proc.communicate(timeout=0)
        except subprocess.TimeoutExpired:
            stdout, stderr = proc.communicate(timeout=1)
        except OSError:
            stdout, stderr = proc.communicate()

        if stdout:
            logger.info("agent 最后输出 (stdout):\n%s", stdout.decode(errors="replace").strip())
        if stderr:
            logger.info("agent 最后输出 (stderr):\n%s", stderr.decode(errors="replace").strip())

        _git_reset_hard()
        proc = _start_agent()

    # 优雅退出
    logger.info("看门狗正在退出 ...")
    if proc is not None:
        _terminate_agent(proc)
    logger.info("看门狗已退出")


if __name__ == "__main__":
    main()
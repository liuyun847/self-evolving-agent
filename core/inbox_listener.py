"""
inbox 目录事件监听模块

基于 watchdog 实现文件系统事件监听（非轮询），
检测 inbox 目录下的新文件并触发回调处理。
"""

import os
import sys
import threading
from collections.abc import Callable
from pathlib import Path

# 通过 importlib 导入 watchdog 包，避免项目根目录的 watchdog.py 命名冲突
import importlib
_watchdog_pkg = importlib.import_module("watchdog")
FileCreatedEvent = _watchdog_pkg.events.FileCreatedEvent
FileSystemEventHandler = _watchdog_pkg.events.FileSystemEventHandler
Observer = _watchdog_pkg.observers.Observer


class _InboxHandler(FileSystemEventHandler):
    """inbox 目录文件事件处理器，处理新文件创建事件"""

    def __init__(self, callback: Callable[[str], None]) -> None:
        """
        :param callback: 收到新文件内容时的回调函数，接收文件内容字符串
        """
        super().__init__()
        self._callback: Callable[[str], None] = callback

    def on_created(self, event: FileCreatedEvent) -> None:
        """处理文件创建事件：读取内容 → 调用回调 → 删除文件"""
        file_path: Path = Path(event.src_path)

        # 忽略目录创建和隐藏文件（如 .gitkeep）
        if event.is_directory or file_path.name.startswith("."):
            return

        try:
            content: str = file_path.read_text(encoding="utf-8")
            self._callback(content)
        except Exception:
            pass
        finally:
            try:
                file_path.unlink(missing_ok=True)
            except Exception:
                pass


class InboxListener:
    """inbox 目录监听器，在独立线程中监听文件创建事件"""

    def __init__(self, inbox_dir: str, callback: Callable[[str], None]) -> None:
        """
        :param inbox_dir: 要监听的 inbox 目录路径
        :param callback: 收到新文件内容时的回调函数
        """
        self._inbox_dir: str = inbox_dir
        self._callback: Callable[[str], None] = callback
        self._observer: Observer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """在独立守护线程中启动文件系统事件监听"""
        if self._thread is not None and self._thread.is_alive():
            return
        os.makedirs(self._inbox_dir, exist_ok=True)
        # 每次 start 创建新的 Observer，支持 stop 后重新 start
        self._observer = Observer()
        self._observer.schedule(
            _InboxHandler(self._callback),
            self._inbox_dir,
            recursive=False,
        )
        self._thread = threading.Thread(
            target=self._observer.start,
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """停止文件系统事件监听并等待线程结束"""
        if self._observer is not None:
            self._observer.stop()
            self._observer = None
        if self._thread is not None:
            self._thread.join()
            self._thread = None
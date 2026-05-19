"""agent.py - Agent 主循环模块

整个自我进化 Agent 系统的核心，负责：
- 事件驱动的主循环（LLM 迭代 + inbox 外部消息）
- 上下文组装（system 提示词 + 对话历史 + 工具定义）
- LLM 调用与 tool_calls 解析
- 工具执行与结果回写
- 锚点保护（禁止修改 watchdog.py 和 core/）
- 文件操作后自动 git add + git commit
- 上下文压缩判断与执行
- 自我重启（检测自身代码修改后退出）
- inbox 外部消息监听与响应
"""

from __future__ import annotations

import json
import logging
import os
import queue
import sys
import threading
from typing import Any

from context_compressor import ContextCompressor
from core import InboxListener, create_default_registry
from core.git_tools import git_add, git_commit, git_status
from core.registry import ToolRegistry
from llm.client import LLMClient

logger = logging.getLogger("agent")

_WORKSPACE: str = os.path.dirname(os.path.abspath(__file__))
"""项目根目录（基于文件所在位置动态计算）"""

_SYSTEM_PROMPT_PATH: str = os.path.join(_WORKSPACE, "memory", "system.md")
"""系统提示词文件路径"""

_INBOX_DIR: str = os.path.join(_WORKSPACE, "inbox")
"""inbox 目录路径"""

_INBOX_RESPONSE_PATH: str = os.path.join(_INBOX_DIR, "response.txt")
"""inbox 响应文件路径"""

_SELF_FILES: frozenset[str] = frozenset({
    os.path.join(_WORKSPACE, "agent.py"),
    os.path.join(_WORKSPACE, "llm", "client.py"),
    os.path.join(_WORKSPACE, "context_compressor.py"),
    os.path.join(_WORKSPACE, "memory", "system.md"),
})
"""触发自我重启的自身源码文件集合"""


class Agent:
    """自我进化 Agent 主循环。

    事件驱动架构，通过 queue.Queue 统一调度 LLM 迭代和外部消息。
    """

    def __init__(self, max_iterations: int = 100) -> None:
        """初始化 Agent 各组件。

        Args:
            max_iterations: 单轮最大 LLM 迭代次数，防止无限循环
        """
        self.max_iterations: int = max_iterations
        self.event_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.registry: ToolRegistry = create_default_registry()
        self.llm_client: LLMClient = LLMClient()
        self.compressor: ContextCompressor = ContextCompressor()
        self.messages: list[dict[str, Any]] = []
        self.inbox_listener: InboxListener = InboxListener(
            _INBOX_DIR, self._on_inbox_message
        )
        self._restart_needed: bool = False

    # ------------------------------------------------------------------
    # 入口
    # ------------------------------------------------------------------

    def run(self) -> None:
        """启动 Agent 主循环和 inbox 监听线程。"""
        self._setup_logging()
        logger.info("Agent 启动中 ...")

        self._initial_git_commit()
        self._load_system_prompt()
        self.inbox_listener.start()
        logger.info("inbox 监听已启动: %s", _INBOX_DIR)

        self.event_queue.put(("llm_iteration", None))

        self._main_loop()

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------

    def _main_loop(self) -> None:
        """事件驱动主循环。

        从 event_queue 取事件，分派到对应处理器。
        事件类型：
            - llm_iteration: LLM 迭代（调用 LLM → 解析 tool_calls → 执行工具）
            - inbox_message: 外部消息（加入对话历史 → 触发 LLM 迭代）
        """
        iteration: int = 0

        while True:
            try:
                event_type, payload = self.event_queue.get(timeout=1)
            except queue.Empty:
                continue

            if event_type == "llm_iteration":
                iteration += 1
                if iteration > self.max_iterations:
                    logger.warning(
                        "达到最大迭代次数 %d，退出主循环", self.max_iterations
                    )
                    break

                logger.info("--- LLM 迭代 %d/%d ---", iteration, self.max_iterations)
                self._process_llm_iteration()

            elif event_type == "inbox_message":
                logger.info("收到 inbox 外部消息")
                self._process_inbox_message(payload)

            if self._restart_needed:
                logger.info("检测到自身代码修改，准备重启 ...")
                self.inbox_listener.stop()
                sys.exit(0)

            if self.compressor.should_compress(self.messages):
                logger.info("上下文过大，执行压缩 ...")
                self.messages = self.compressor.compress(self.messages, self.llm_client)
                logger.info("上下文压缩完成，当前消息数: %d", len(self.messages))

        logger.info("Agent 主循环结束")

    # ------------------------------------------------------------------
    # LLM 迭代
    # ------------------------------------------------------------------

    def _process_llm_iteration(self) -> None:
        """执行一次 LLM 迭代：调用 LLM → 解析 tool_calls → 执行工具 → 回写结果。"""
        content, tool_calls = self._call_llm()

        assistant_msg: dict[str, Any] = {"role": "assistant", "content": content}
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls

        self.messages.append(assistant_msg)

        if not tool_calls:
            logger.info("LLM 响应（无 tool_calls）: %s", content[:200])
            self.event_queue.put(("llm_iteration", None))
            return

        logger.info("LLM 返回 %d 个 tool_calls", len(tool_calls))

        for tc in tool_calls:
            func_name: str = tc["function"]["name"]
            func_args: dict[str, Any] = self._parse_tool_args(tc)
            tc_id: str = tc["id"]

            logger.info("执行工具: %s(%s)", func_name, func_args)

            anchor_error: str | None = self._check_anchor(func_name, func_args)
            if anchor_error is not None:
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": anchor_error,
                })
                continue

            try:
                result: Any = self.registry.call(func_name, **func_args)
                result_str: str = str(result)
                logger.info("工具 %s 执行成功，结果长度: %d", func_name, len(result_str))
            except Exception as exc:
                result_str = f"工具执行异常: {type(exc).__name__}: {exc}"
                logger.warning("工具 %s 执行失败: %s", func_name, result_str)

            self.messages.append({
                "role": "tool",
                "tool_call_id": tc_id,
                "content": result_str,
            })

            self._auto_git_commit(func_name, func_args)

        self.event_queue.put(("llm_iteration", None))

    # ------------------------------------------------------------------
    # LLM 调用
    # ------------------------------------------------------------------

    def _call_llm(self) -> tuple[str, list[dict[str, Any]]]:
        """调用 LLM API，返回 (文本内容, tool_calls 列表)。

        通过 LLMClient._retry() 执行调用，确保享受指数退避重试保护。

        Returns:
            (响应文本, tool_calls 字典列表)
        """
        tool_schemas: list[dict[str, Any]] = self.registry.get_tool_schemas()

        kwargs: dict[str, Any] = {
            "model": self.llm_client._model,
            "messages": self.messages,
            "temperature": 0.7,
            "max_tokens": self.llm_client._max_tokens,
        }
        if tool_schemas:
            kwargs["tools"] = tool_schemas

        response = self.llm_client._retry_simple(
            lambda: self.llm_client._client.chat.completions.create(**kwargs)
        )

        return self._parse_response(response)

    # ------------------------------------------------------------------
    # 响应解析
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(
        response: Any,
    ) -> tuple[str, list[dict[str, Any]]]:
        """从 ChatCompletion 响应中提取文本内容和 tool_calls。

        Args:
            response: OpenAI ChatCompletion 对象

        Returns:
            (响应文本, tool_calls 字典列表)
        """
        choice = response.choices[0]
        content: str = choice.message.content or ""
        tool_calls: list[dict[str, Any]] = []

        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                })

        return content, tool_calls

    # ------------------------------------------------------------------
    # 工具参数解析
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_tool_args(tool_call: dict[str, Any]) -> dict[str, Any]:
        """将 tool_call 中的 arguments JSON 字符串解析为 dict。

        Args:
            tool_call: 单个 tool_call 字典

        Returns:
            解析后的参数字典，解析失败返回含错误信息的字典
        """
        args_str: str = tool_call["function"].get("arguments", "{}")
        try:
            return json.loads(args_str)
        except json.JSONDecodeError:
            logger.warning("工具参数 JSON 解析失败: %s", args_str)
            return {"_parse_error": f"JSON 解析失败: {args_str}"}

    # ------------------------------------------------------------------
    # 锚点保护
    # ------------------------------------------------------------------

    @staticmethod
    def _check_anchor(tool_name: str, args: dict[str, Any]) -> str | None:
        """检查文件操作是否触碰锚点（watchdog.py 或 core/ 目录）。

        Args:
            tool_name: 工具名称
            args: 工具参数字典

        Returns:
            若触碰锚点则返回错误消息，否则返回 None
        """
        if tool_name not in ("write_file", "delete_file"):
            return None

        target_path: str = args.get("path", "")
        if not target_path:
            return None

        abs_path: str = os.path.abspath(target_path)
        core_dir: str = os.path.join(_WORKSPACE, "core")
        watchdog_path: str = os.path.join(_WORKSPACE, "watchdog.py")

        if abs_path == watchdog_path:
            return (
                "❌ 锚点保护: 禁止修改 watchdog.py。"
                "该文件是看门狗进程，不可被 Agent 修改。"
            )
        if abs_path.startswith(core_dir + os.sep) or abs_path == core_dir:
            return (
                f"❌ 锚点保护: 禁止修改 core/ 目录下的文件 ({target_path})。"
                "core/ 为只读锚点区域。"
            )

        return None

    # ------------------------------------------------------------------
    # 自动 git commit
    # ------------------------------------------------------------------

    def _auto_git_commit(self, tool_name: str, args: dict[str, Any]) -> None:
        """文件操作后自动 git add + git commit。

        仅对 write_file / append_file / delete_file 操作触发。

        Args:
            tool_name: 工具名称
            args: 工具参数字典
        """
        if tool_name not in ("write_file", "append_file", "delete_file"):
            return

        target_path: str = args.get("path", "")
        if not target_path:
            return

        logger.info("自动 git add + commit: %s", target_path)
        git_add(target_path)

        commit_msg: str = f"auto: {tool_name} {target_path}"
        git_commit(commit_msg)

        abs_path: str = os.path.abspath(target_path)
        if abs_path in _SELF_FILES:
            logger.info("检测到自身源码修改: %s，标记需要重启", target_path)
            self._restart_needed = True

    # ------------------------------------------------------------------
    # inbox 处理
    # ------------------------------------------------------------------

    def _on_inbox_message(self, content: str) -> None:
        """inbox 收到外部消息时的回调（在 InboxListener 线程中调用）。

        将消息推入事件队列，由主循环线程处理。

        Args:
            content: 消息文本内容
        """
        self.event_queue.put(("inbox_message", content))

    def _process_inbox_message(self, content: str) -> None:
        """处理 inbox 外部消息。

        将消息加入对话历史，触发 LLM 迭代，处理完成后写入响应文件。

        Args:
            content: 消息文本内容
        """
        self.messages.append({"role": "user", "content": content})
        self.event_queue.put(("llm_iteration", None))

        self._wait_and_write_response(content)

    def _wait_and_write_response(self, user_content: str) -> None:
        """等待 inbox 消息处理完成并写入响应文件。

        在独立线程中运行，轮询直到 LLM 产生新的 assistant 响应后写入。

        Args:
            user_content: 原始用户消息（用于日志）
        """
        def _worker() -> None:
            import time

            msg_count_before: int = len(self.messages)
            timeout: float = 120.0
            start: float = time.time()

            while time.time() - start < timeout:
                if len(self.messages) > msg_count_before:
                    last_msg: dict[str, Any] = self.messages[-1]
                    if last_msg.get("role") == "assistant" and not last_msg.get("tool_calls"):
                        response_text: str = last_msg.get("content", "")
                        self._write_inbox_response(response_text)
                        return
                time.sleep(0.5)

            self._write_inbox_response("处理超时，未能在 120 秒内完成响应。")

        threading.Thread(target=_worker, daemon=True).start()

    @staticmethod
    def _write_inbox_response(text: str) -> None:
        """将响应文本写入 inbox/response.txt。

        Args:
            text: 响应文本
        """
        try:
            os.makedirs(_INBOX_DIR, exist_ok=True)
            with open(_INBOX_RESPONSE_PATH, "w", encoding="utf-8") as f:
                f.write(text)
            logger.info("inbox 响应已写入: %s", _INBOX_RESPONSE_PATH)
        except OSError as exc:
            logger.error("写入 inbox 响应失败: %s", exc)

    # ------------------------------------------------------------------
    # 初始化
    # ------------------------------------------------------------------

    @staticmethod
    def _setup_logging() -> None:
        """配置日志格式与级别。"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            stream=sys.stdout,
        )

    def _load_system_prompt(self) -> None:
        """从 memory/system.md 加载系统提示词并初始化为 messages[0]。"""
        try:
            with open(_SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
                system_content: str = f.read()
        except FileNotFoundError:
            logger.warning("系统提示词文件未找到: %s，使用默认提示词", _SYSTEM_PROMPT_PATH)
            system_content = "你是一个自我进化的 AI Agent。"

        self.messages = [{"role": "system", "content": system_content}]
        logger.info("系统提示词已加载，长度: %d 字符", len(system_content))

    @staticmethod
    def _initial_git_commit() -> None:
        """启动时检查工作区状态，若有未提交变更则执行一次初始 git commit。"""
        status_output: str = git_status()
        if status_output:
            logger.info("工作区有未提交变更，执行初始 git commit")
            git_add(".")
            git_commit("init: Agent 启动前的初始提交")
        else:
            logger.info("工作区干净，无需初始 git commit")


# ------------------------------------------------------------------
# 入口
# ------------------------------------------------------------------

if __name__ == "__main__":
    Agent().run()
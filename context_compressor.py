"""
上下文压缩器模块 - 用于管理和压缩 LLM 对话上下文。

当消息列表的预估 token 数超过阈值（MAX_TOKENS * 0.8）时，自动压缩：
- 保留 system 消息
- 保留最近 N 条消息
- 将中间旧消息替换为摘要，控制 token 用量
"""

from __future__ import annotations

import os
import re
from typing import Any, Callable, Optional


def _count_chinese_chars(text: str) -> int:
    """统计文本中的中文字符数（含中文标点）"""
    count = 0
    for ch in text:
        cp = ord(ch)
        if (
            0x4E00 <= cp <= 0x9FFF
            or 0x3400 <= cp <= 0x4DBF
            or 0x3000 <= cp <= 0x303F
            or 0xFF00 <= cp <= 0xFFEF
            or 0x2000 <= cp <= 0x206F
        ):
            count += 1
    return count


def _count_english_tokens(text: str) -> float:
    """
    统计文本中非中文部分的 token 估算值。

    移除中文字符后，按约 4 个字符 ≈ 1 token 估算。
    """
    cleaned = re.sub(r"[\u4e00-\u9fff\u3400-\u4dbf\u3000-\u303f\uff00-\uffef\u2000-\u206f]", "", text)
    cleaned = cleaned.strip()
    if not cleaned:
        return 0.0
    return len(cleaned) / 4.0


def estimate_tokens(text: str) -> int:
    """
    估算文本的 token 数量。

    估算规则：
    - 中文字符（含中文标点）：约 1 字符 ≈ 1.5 token
    - 英文/其他字符：约 4 字符 ≈ 1 token

    返回向上取整的整数。
    """
    chinese_chars = _count_chinese_chars(text)
    english_tokens = _count_english_tokens(text)
    raw = chinese_chars * 1.5 + english_tokens
    return max(1, int(raw + 0.999))  # 向上取整，至少为 1


class ContextCompressor:
    """
    上下文压缩器。

    当消息列表的预估 token 数超过阈值时，将中间旧消息压缩为摘要，
    同时保留 system 消息和最近的消息。

    Usage::

        compressor = ContextCompressor()
        if compressor.should_compress(messages):
            messages = compressor.compress(messages)
    """

    def __init__(self, max_tokens: Optional[int] = None) -> None:
        """
        初始化压缩器。

        :param max_tokens: 最大 token 数，默认从环境变量 LLM_MAX_TOKENS 读取，
                           若未设置则使用 128000
        """
        if max_tokens is None:
            max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "128000"))
        self.max_tokens: int = max_tokens
        self.threshold: int = int(max_tokens * 0.8)

    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的 token 数量（委托模块级函数）。
        """
        return estimate_tokens(text)

    def _messages_tokens(self, messages: list[dict[str, Any]]) -> int:
        """估算整个消息列表的 token 总数"""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += self.estimate_tokens(content)
            # 每条消息约有 4 token 的格式开销（role 标记等）
            total += 4
        return total

    def should_compress(self, messages: list[dict[str, Any]]) -> bool:
        """
        判断消息列表是否需要压缩。

        :param messages: OpenAI 兼容的消息列表
        :return: 若预估 token 数超过阈值则返回 True
        """
        return self._messages_tokens(messages) > self.threshold

    def compress(
        self,
        messages: list[dict[str, Any]],
        llm_client: Optional[Any] = None,
    ) -> list[dict[str, Any]]:
        """
        压缩消息列表，返回新的消息列表，不修改原列表。

        压缩策略：
        1. 保留第一条 system 消息（若存在）
        2. 保留最近 N 条消息，确保它们的 token 数不超过阈值
        3. 将 system 与最近消息之间的旧消息替换为一条摘要消息

        :param messages: OpenAI 兼容的消息列表
        :param llm_client: 可选的 LLM 客户端，用于生成摘要；
                           若未提供则使用简单文本截断方式生成摘要
        :return: 压缩后的消息列表
        """
        if not messages:
            return []

        # 分离 system 消息与其他消息
        system_msg: Optional[dict[str, Any]] = None
        rest: list[dict[str, Any]] = []
        if messages and messages[0].get("role") == "system":
            system_msg = messages[0]
            rest = messages[1:]
        else:
            rest = list(messages)

        if not rest:
            return list(messages)

        # 从后往前选取最近消息，直到接近阈值
        system_tokens = self._messages_tokens([system_msg]) if system_msg else 0
        # 确保 available 至少为 threshold 的 10%，避免 system 消息过大时为负
        available = max(self.threshold // 10, self.threshold - system_tokens - 200)

        kept_indices: list[int] = []
        kept_tokens = 0
        i = len(rest) - 1
        while i >= 0:
            msg = rest[i]
            msg_tokens = self.estimate_tokens(
                msg.get("content", "") if isinstance(msg.get("content"), str) else ""
            ) + 4
            if kept_indices and kept_tokens + msg_tokens > available:
                break
            kept_indices.insert(0, i)
            kept_tokens += msg_tokens
            i -= 1

        # 保护 tool_calls 配对：若 kept 第一条是 tool 结果，
        # 向前扩展直到包含对应的 assistant tool_calls 消息
        while kept_indices:
            first_idx = kept_indices[0]
            if rest[first_idx].get("role") != "tool":
                break
            if first_idx == 0:
                break
            prev_idx = first_idx - 1
            prev_msg = rest[prev_idx]
            if prev_msg.get("role") == "assistant" and prev_msg.get("tool_calls"):
                kept_indices.insert(0, prev_idx)
            elif prev_msg.get("role") == "tool":
                kept_indices.insert(0, prev_idx)
                continue
            else:
                break

        kept = [rest[idx] for idx in kept_indices]

        # 确定需要摘要的旧消息范围
        if not kept_indices:
            kept = [rest[-1]]
            kept_start_idx = len(rest) - 1
        else:
            kept_start_idx = kept_indices[0]

        old_messages = rest[:kept_start_idx]

        if not old_messages:
            return list(messages)

        # 生成摘要
        summary = self._generate_summary(old_messages, llm_client)

        # 组装结果
        result: list[dict[str, Any]] = []
        if system_msg:
            result.append(system_msg)
        result.append({"role": "user", "content": summary})
        result.extend(kept)

        return result

    def _generate_summary(
        self,
        old_messages: list[dict[str, Any]],
        llm_client: Optional[Any] = None,
    ) -> str:
        """
        为旧消息生成摘要。

        :param old_messages: 需要摘要的旧消息列表
        :param llm_client: 可选的 LLM 客户端
        :return: 摘要文本
        """
        # 拼接旧消息内容
        parts: list[str] = []
        for msg in old_messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if isinstance(content, str):
                parts.append(f"[{role}]: {content}")
            elif isinstance(content, list):
                text_parts = [
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                ]
                parts.append(f"[{role}]: {' '.join(text_parts)}")
        combined = "\n".join(parts)

        if llm_client is not None:
            return self._llm_summary(llm_client, combined)
        else:
            return self._simple_summary(combined)

    def _simple_summary(self, text: str, max_summary_chars: int = 500) -> str:
        """
        简单截断方式生成摘要：取文本开头部分。

        :param text: 原始文本
        :param max_summary_chars: 摘要最大字符数
        :return: 截断后的摘要文本
        """
        if len(text) <= max_summary_chars:
            return f"[历史对话摘要]\n{text}"
        return f"[历史对话摘要]\n{text[:max_summary_chars]}..."

    def _llm_summary(self, llm_client: Any, text: str) -> str:
        """
        使用 LLM 客户端生成摘要。

        :param llm_client: 需支持 chat() 接口的 LLM 客户端
        :param text: 待摘要的文本
        :return: LLM 生成的摘要
        """
        prompt = (
            "请将以下对话历史总结为简洁的摘要，保留关键信息和决策：\n\n"
            + text
        )
        try:
            summary = llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3,
            )
            return f"[历史对话摘要]\n{summary}"
        except Exception:
            return self._simple_summary(text)
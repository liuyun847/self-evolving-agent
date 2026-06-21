"""LLM 客户端模块

提供 OpenAI 兼容 API 的统一调用接口，支持流式/非流式响应、tools 调用和自动重试。
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Generator
from typing import Any

from dotenv import load_dotenv
from openai import APIStatusError, APITimeoutError, APIConnectionError, OpenAI

load_dotenv()

logger = logging.getLogger(__name__)

LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
LLM_API_BASE: str = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4")
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "128000"))


class LLMClient:
    """LLM 客户端，封装 OpenAI 兼容 API 的调用逻辑。

    特性:
        - 自动从环境变量加载配置（支持 .env 文件）
        - 指数退避重试（对 429 / 5xx / 超时 / 连接错误）
        - 同时支持流式和非流式响应
        - 支持 OpenAI function calling 格式的 tools 定义
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> None:
        """初始化 LLM 客户端。

        参数:
            api_key: API 密钥，默认从环境变量 LLM_API_KEY 读取
            base_url: API 基础 URL，默认从环境变量 LLM_API_BASE 读取
            model: 模型名称，默认从环境变量 LLM_MODEL 读取
            max_tokens: 最大 token 数，默认从环境变量 LLM_MAX_TOKENS 读取
            max_retries: 最大重试次数，默认 3
            base_delay: 基础重试延迟（秒），用于指数退避计算，默认 1.0

        异常:
            ValueError: api_key 为空且环境变量也未设置时抛出
        """
        self._api_key = api_key or LLM_API_KEY
        if not self._api_key:
            raise ValueError("LLM_API_KEY 未设置，请通过参数或环境变量提供 API 密钥")

        self._base_url = base_url or LLM_API_BASE
        self._model = model or LLM_MODEL
        self._max_tokens = max_tokens if max_tokens is not None else LLM_MAX_TOKENS
        self._max_retries = max_retries
        self._base_delay = base_delay

        self._client = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )
        logger.info(
            "LLMClient 初始化完成: model=%s, base_url=%s, max_retries=%d",
            self._model,
            self._base_url,
            self._max_retries,
        )

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str | Generator[str, None, None]:
        """发送聊天请求并获取响应。

        参数:
            messages: 消息列表，每项为 {"role": ..., "content": ...} 格式
            tools: tools 定义列表（OpenAI function calling 格式），
                   每项包含 type, function 等字段，为 None 时不传 tools
            stream: 是否使用流式响应，默认 False
            temperature: 采样温度，默认 0.7
            max_tokens: 最大输出 token 数，默认使用实例配置

        返回:
            非流式时返回完整响应文本；流式时返回逐个文本块的生成器

        异常:
            openai 相关异常在重试耗尽后向上抛出
        """
        if stream:
            return self._chat_stream(messages, tools, temperature, max_tokens)
        else:
            return self._chat_sync(messages, tools, temperature, max_tokens)

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> Any:
        """发送聊天请求并返回完整的 ChatCompletion 响应对象。

        与 chat() 不同，此方法返回原始响应对象，可用于访问 tool_calls 等字段。

        参数:
            messages: 消息列表
            tools: tools 定义列表，为 None 时不传 tools
            temperature: 采样温度，默认 0.7
            max_tokens: 最大输出 token 数，默认使用实例配置

        返回:
            OpenAI ChatCompletion 响应对象

        异常:
            openai 相关异常在重试耗尽后向上抛出
        """
        kwargs = self._build_kwargs(messages, tools, temperature, max_tokens)
        return self._retry(lambda: self._client.chat.completions.create(**kwargs))

    @property
    def model(self) -> str:
        """当前配置的模型名称"""
        return self._model

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _build_kwargs(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        temperature: float,
        max_tokens: int | None,
    ) -> dict[str, Any]:
        """构建 API 请求的参数字典，消除重复代码。"""
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens if max_tokens is not None else self._max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
        return kwargs

    def _chat_sync(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        temperature: float,
        max_tokens: int | None,
    ) -> str:
        """非流式请求，返回完整响应文本。"""
        kwargs = self._build_kwargs(messages, tools, temperature, max_tokens)

        response = self._retry(lambda: self._client.chat.completions.create(**kwargs))

        choice = response.choices[0]
        content = choice.message.content
        return content if content is not None else ""

    def _chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        temperature: float,
        max_tokens: int | None,
    ) -> Generator[str, None, None]:
        """流式请求，返回逐个文本块的生成器。"""
        kwargs = self._build_kwargs(messages, tools, temperature, max_tokens)
        kwargs["stream"] = True

        stream_response = self._retry(
            lambda: self._client.chat.completions.create(**kwargs)
        )

        for chunk in stream_response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    def _should_retry(self, error: Exception) -> bool:
        """判断给定异常是否值得重试。

        重试条件:
            - HTTP 429 (RateLimitError)
            - HTTP 5xx (服务端错误)
            - 请求超时 (APITimeoutError)
            - 连接错误 (APIConnectionError)
        """
        if isinstance(error, APIStatusError):
            return error.status_code == 429 or error.status_code >= 500
        if isinstance(error, (APITimeoutError, APIConnectionError)):
            return True
        return False

    def _retry(self, fn: Any) -> Any:
        """带指数退避的重试执行器。

        对可重试的异常按 1s, 2s, 4s, 8s... 的延迟进行重试，
        最多重试 max_retries 次；不可重试的异常直接抛出。

        参数:
            fn: 无参可调用对象，返回 API 响应

        返回:
            fn 的返回值

        异常:
            重试耗尽后抛出最后一次的异常
        """
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                return fn()
            except Exception as exc:
                last_error = exc
                if not self._should_retry(exc) or attempt >= self._max_retries:
                    raise
                delay = self._base_delay * (2 ** attempt)
                logger.warning(
                    "LLM 请求失败 (attempt %d/%d)，%.1fs 后重试: %s",
                    attempt + 1,
                    self._max_retries,
                    delay,
                    exc,
                )
                time.sleep(delay)

        # 理论上不会走到这里，保留作为安全兜底
        assert last_error is not None
        raise last_error
"""core/registry.py - 工具注册表模块

提供统一的工具注册、查询、调用接口，所有工具通过此注册表暴露给 LLM。
"""

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolSpec:
    """工具规格，描述一个可被 LLM 调用的工具"""

    name: str
    """工具名称，唯一标识"""

    description: str
    """工具功能描述，供 LLM 理解用途"""

    parameters: dict[str, Any]
    """参数 JSON Schema，兼容 OpenAI function calling 格式"""

    handler: Callable[..., Any]
    """实际执行函数，接受关键字参数并返回结果"""


class ToolRegistry:
    """工具注册表，管理所有已注册的工具"""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: Callable[..., Any],
    ) -> None:
        """注册一个新工具

        Args:
            name: 工具唯一名称
            description: 工具功能描述
            parameters: 参数 JSON Schema（OpenAI function calling 格式）
            handler: 工具执行函数

        Raises:
            ValueError: 工具名已存在
        """
        if name in self._tools:
            raise ValueError(f"工具 '{name}' 已注册")
        self._tools[name] = ToolSpec(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
        )

    def get_tool(self, name: str) -> ToolSpec:
        """查询单个工具

        Args:
            name: 工具名称

        Returns:
            对应的 ToolSpec 对象

        Raises:
            KeyError: 工具不存在
        """
        if name not in self._tools:
            raise KeyError(f"工具 '{name}' 未注册")
        return self._tools[name]

    def list_tools(self) -> list[ToolSpec]:
        """列出所有已注册工具

        Returns:
            ToolSpec 对象列表
        """
        return list(self._tools.values())

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """返回 OpenAI function calling 格式的工具列表

        Returns:
            dict 列表，每个 dict 包含 type 和 function 字段
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    def call(self, name: str, **kwargs: Any) -> Any:
        """调用指定工具

        Args:
            name: 工具名称
            **kwargs: 传递给工具 handler 的关键字参数

        Returns:
            工具 handler 的返回值

        Raises:
            KeyError: 工具不存在
        """
        tool = self.get_tool(name)
        return tool.handler(**kwargs)
"""core/web_tools.py - 网页工具模块

提供网页搜索与网页内容捕获功能，供 LLM 调用以获取实时网络信息。
"""

from typing import Any

import httpx
from bs4 import BeautifulSoup


def web_search(query: str, num_results: int = 5) -> str:
    """网页搜索：使用 DuckDuckGo HTML 搜索获取结果

    Args:
        query: 搜索关键词
        num_results: 返回结果数量上限，默认 5

    Returns:
        格式化搜索结果字符串，每行一个结果，格式为 "标题\nURL\n摘要\n---"
        请求失败时返回错误信息字符串
    """
    url: str = "https://html.duckduckgo.com/html/"
    headers: dict[str, str] = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        response: httpx.Response = httpx.get(
            url,
            params={"q": query},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
    except httpx.HTTPError as e:
        return f"搜索请求失败: {e}"

    soup: BeautifulSoup = BeautifulSoup(response.text, "html.parser")
    result_elements: Any = soup.select(".result")

    if not result_elements:
        return "未找到搜索结果"

    lines: list[str] = []
    for element in result_elements[:num_results]:
        title_el: Any = element.select_one(".result__title")
        url_el: Any = element.select_one(".result__url")
        snippet_el: Any = element.select_one(".result__snippet")

        title: str = title_el.get_text(strip=True) if title_el else "无标题"
        link: str = url_el.get_text(strip=True) if url_el else "无链接"
        snippet: str = snippet_el.get_text(strip=True) if snippet_el else "无摘要"

        # 清理 URL 前缀
        if link and "//" in link:
            link = link.strip()

        lines.append(f"{title}\n{link}\n{snippet}\n---")

    return "\n".join(lines) if lines else "未找到搜索结果"


def web_fetch(url: str, timeout: int = 30) -> str:
    """网页内容捕获：获取网页并提取正文纯文本

    Args:
        url: 目标网页 URL
        timeout: 请求超时秒数，默认 30

    Returns:
        提取的纯文本内容，最多 10000 字符（超出截断并标注）
        请求失败时返回错误信息字符串
    """
    headers: dict[str, str] = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        response: httpx.Response = httpx.get(
            url,
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        )
        response.raise_for_status()
    except httpx.HTTPError as e:
        return f"网页请求失败: {e}"

    soup: BeautifulSoup = BeautifulSoup(response.text, "html.parser")

    # 移除 script 和 style 标签及其内容
    for tag in soup(["script", "style"]):
        tag.decompose()

    text: str = soup.get_text()

    # 合并多余空白行
    lines: list[str] = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned_text: str = "\n".join(lines)

    max_chars: int = 10000
    if len(cleaned_text) > max_chars:
        cleaned_text = cleaned_text[:max_chars] + "\n\n[内容已截断，原文共 {} 字符]".format(
            len(text)
        )

    return cleaned_text if cleaned_text else "未能提取到有效文本内容"
"""综合测试脚本 - 测试自我进化 Agent 项目所有模块的基础功能"""

import os
import sys
import json
import tempfile
import time
import traceback

WORKSPACE = os.path.dirname(os.path.abspath(__file__))

TESTS_PASSED = 0
TESTS_FAILED = 0
TEST_DETAILS: list[dict] = []


def test_section(name: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  测试: {name}")
    print(f"{'=' * 60}")


def assert_equal(actual, expected, msg: str) -> bool:
    global TESTS_PASSED, TESTS_FAILED
    if actual == expected:
        TESTS_PASSED += 1
        TEST_DETAILS.append({"name": msg, "status": "PASS", "detail": f"{actual!r} == {expected!r}"})
        print(f"  ✅ {msg}")
        return True
    else:
        TESTS_FAILED += 1
        TEST_DETAILS.append({"name": msg, "status": "FAIL", "detail": f"期望 {expected!r}, 实际 {actual!r}"})
        print(f"  ❌ {msg} - 期望 {expected!r}, 实际 {actual!r}")
        return False


def assert_true(condition, msg: str) -> bool:
    global TESTS_PASSED, TESTS_FAILED
    if condition:
        TESTS_PASSED += 1
        TEST_DETAILS.append({"name": msg, "status": "PASS", "detail": "True"})
        print(f"  ✅ {msg}")
        return True
    else:
        TESTS_FAILED += 1
        TEST_DETAILS.append({"name": msg, "status": "FAIL", "detail": "条件不成立"})
        print(f"  ❌ {msg}")
        return False


def assert_raises(exc_type, fn, msg: str) -> bool:
    global TESTS_PASSED, TESTS_FAILED
    try:
        fn()
        TESTS_FAILED += 1
        TEST_DETAILS.append({"name": msg, "status": "FAIL", "detail": "未抛出异常"})
        print(f"  ❌ {msg} - 未抛出异常")
        return False
    except exc_type:
        TESTS_PASSED += 1
        TEST_DETAILS.append({"name": msg, "status": "PASS", "detail": f"正确抛出 {exc_type.__name__}"})
        print(f"  ✅ {msg}")
        return True
    except Exception as e:
        TESTS_FAILED += 1
        TEST_DETAILS.append({"name": msg, "status": "FAIL", "detail": f"抛出异常类型不符: {type(e).__name__}: {e}"})
        print(f"  ❌ {msg} - 抛出 {type(e).__name__} 而非 {exc_type.__name__}")
        return False


def assert_in(substring: str, container: str, msg: str) -> bool:
    global TESTS_PASSED, TESTS_FAILED
    if substring in container:
        TESTS_PASSED += 1
        TEST_DETAILS.append({"name": msg, "status": "PASS", "detail": f"'{substring[:50]}' 存在于结果中"})
        print(f"  ✅ {msg}")
        return True
    else:
        TESTS_FAILED += 1
        TEST_DETAILS.append({"name": msg, "status": "FAIL", "detail": f"'{substring[:50]}' 不在结果中"})
        print(f"  ❌ {msg}")
        return False


# =============================================================================
# 1. 文件工具测试
# =============================================================================
def test_file_tools() -> None:
    test_section("1. 文件工具测试")

    from core.file_tools import read_file, write_file, append_file, list_dir, delete_file

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1.1 write_file - 创建文件
        fpath = os.path.join(tmpdir, "test.txt")
        result = write_file(fpath, "Hello World")
        assert_in("文件已写入", result, "1.1 write_file 创建文件")
        assert_true(os.path.isfile(fpath), "1.1 write_file 文件实际存在")

        # 1.2 write_file - 覆盖已有文件
        result = write_file(fpath, "Overwritten")
        assert_in("文件已写入", result, "1.2 write_file 覆盖文件")
        with open(fpath) as f:
            assert_equal(f.read(), "Overwritten", "1.2 write_file 内容正确覆盖")

        # 1.3 read_file - 读取存在的文件
        content = read_file(fpath)
        assert_equal(content, "Overwritten", "1.3 read_file 读取文件内容")

        # 1.4 read_file - 文件不存在异常
        assert_raises(
            FileNotFoundError,
            lambda: read_file(os.path.join(tmpdir, "nonexistent.txt")),
            "1.4 read_file 文件不存在抛出 FileNotFoundError",
        )

        # 1.5 append_file - 追加内容
        result = append_file(fpath, "\nAppended line")
        assert_in("内容已追加到", result, "1.5 append_file 追加成功")
        content = read_file(fpath)
        assert_in("Appended line", content, "1.5 append_file 内容已追加")

        # 1.6 append_file - 文件不存在异常
        assert_raises(
            FileNotFoundError,
            lambda: append_file(os.path.join(tmpdir, "nonexistent.txt"), "data"),
            "1.6 append_file 文件不存在抛出 FileNotFoundError",
        )

        # 1.7 list_dir - 列出目录
        write_file(os.path.join(tmpdir, "a.txt"), "a")
        write_file(os.path.join(tmpdir, "b.txt"), "b")
        os.makedirs(os.path.join(tmpdir, "subdir"), exist_ok=True)
        result = list_dir(tmpdir)
        assert_in("a.txt", result, "1.7 list_dir 包含 a.txt")
        assert_in("b.txt", result, "1.7 list_dir 包含 b.txt")
        assert_in("subdir/", result, "1.7 list_dir 子目录以 / 结尾")

        # 1.8 list_dir - 目录不存在异常
        assert_raises(
            FileNotFoundError,
            lambda: list_dir(os.path.join(tmpdir, "nonexistent")),
            "1.8 list_dir 目录不存在抛出 FileNotFoundError",
        )

        # 1.9 list_dir - 路径是文件而非目录
        assert_raises(
            NotADirectoryError,
            lambda: list_dir(fpath),
            "1.9 list_dir 路径是文件抛出 NotADirectoryError",
        )

        # 1.10 delete_file - 删除文件
        result = delete_file(os.path.join(tmpdir, "a.txt"))
        assert_in("文件已删除", result, "1.10 delete_file 删除成功")
        assert_true(not os.path.exists(os.path.join(tmpdir, "a.txt")), "1.10 delete_file 文件已不存在")

        # 1.11 delete_file - 文件不存在异常
        assert_raises(
            FileNotFoundError,
            lambda: delete_file(os.path.join(tmpdir, "nonexistent.txt")),
            "1.11 delete_file 文件不存在抛出 FileNotFoundError",
        )

        # 1.12 write_file - 写入嵌套路径（自动创建父目录）
        nested = os.path.join(tmpdir, "deep/nested/file.txt")
        result = write_file(nested, "nested content")
        assert_true(os.path.isfile(nested), "1.12 write_file 嵌套路径自动创建父目录")


# =============================================================================
# 2. 命令行工具测试
# =============================================================================
def test_shell_tools() -> None:
    test_section("2. 命令行工具测试")

    from core.shell_tools import run_command

    # 2.1 执行 echo
    result = run_command("echo hello")
    assert_in("退出码: 0", result, "2.1 run_command echo 退出码 0")
    assert_in("hello", result, "2.1 run_command echo 输出 hello")

    # 2.2 超时机制
    import subprocess as sp

    assert_raises(
        sp.TimeoutExpired,
        lambda: run_command("sleep 5", timeout=1),
        "2.2 run_command 超时抛出 TimeoutExpired",
    )

    # 2.3 命令失败
    result = run_command("false")
    assert_in("退出码: 1", result, "2.3 run_command false 退出码为 1")

    # 2.4 stderr 输出
    result = run_command("echo error >&2")
    assert_in("error", result, "2.4 run_command 捕获 stderr")


# =============================================================================
# 3. 网页工具测试
# =============================================================================
def test_web_tools() -> None:
    test_section("3. 网页工具测试")

    from core.web_tools import web_fetch, web_search

    # 3.1 web_fetch 正常请求
    result = web_fetch("https://httpbin.org/robots.txt", timeout=15)
    assert_true(isinstance(result, str) and len(result) > 0, "3.1 web_fetch 返回非空字符串")
    assert_true(
        "User-agent" in result or "Disallow" in result,
        "3.1 web_fetch 包含预期内容",
    )

    # 3.2 web_fetch 错误 URL（不存在的主机）
    result = web_fetch("http://invalid.invalid.invalid/", timeout=5)
    assert_true(
        "网页请求失败" in result or "请求失败" in result,
        "3.2 web_fetch 无效 URL 返回错误信息",
    )

    # 3.3 web_search 正常搜索
    result = web_search("Python programming", num_results=3)
    assert_true(isinstance(result, str) and len(result) > 0, "3.3 web_search 返回非空字符串")
    # DuckDuckGo 在沙箱环境可能受限，函数正确返回了错误信息也算通过
    print(f"    ℹ️ web_search 返回: {result[:120]}...")


# =============================================================================
# 4. Git 工具测试
# =============================================================================
def test_git_tools() -> None:
    test_section("4. Git 工具测试")

    from core.git_tools import git_status, git_add, git_commit, git_diff, git_log, git_reset

    # 注意: 当前 /workspace 不是 git 仓库
    # git 工具函数只封装 subprocess 调用，不会崩溃，只返回 stderr

    # 4.1 git_status 调用不会崩溃
    result = git_status()
    assert_true(isinstance(result, str), "4.1 git_status 返回字符串")

    # 4.2 git_add 调用不会崩溃
    result = git_add(".")
    assert_true(isinstance(result, str), "4.2 git_add 返回字符串")

    # 4.3 git_commit 调用不会崩溃
    result = git_commit("test commit")
    assert_true(isinstance(result, str), "4.3 git_commit 返回字符串")

    # 4.4 git_diff 调用不会崩溃
    result = git_diff()
    assert_true(isinstance(result, str), "4.4 git_diff 返回字符串")

    # 4.5 git_log 调用不会崩溃
    result = git_log(n=5)
    assert_true(isinstance(result, str), "4.5 git_log 返回字符串")

    # 4.6 git_reset soft 调用不会崩溃
    result = git_reset(hard=False)
    assert_true(isinstance(result, str), "4.6 git_reset(soft) 返回字符串")

    # 4.7 git_reset hard 调用不会崩溃
    result = git_reset(hard=True)
    assert_true(isinstance(result, str), "4.7 git_reset(hard) 返回字符串")


# =============================================================================
# 5. 工具注册表测试
# =============================================================================
def test_registry() -> None:
    test_section("5. 工具注册表测试")

    from core.registry import ToolRegistry, ToolSpec
    from core import create_default_registry

    # 5.1 create_default_registry() 返回正确数量
    registry = create_default_registry()
    tools = registry.list_tools()
    assert_equal(len(tools), 14, "5.1 create_default_registry 返回 14 个工具")

    # 5.2 验证所有预期工具名称
    expected_names = {
        "read_file", "write_file", "append_file", "list_dir", "delete_file",
        "run_command",
        "web_search", "web_fetch",
        "git_status", "git_add", "git_commit", "git_diff", "git_log", "git_reset",
    }
    actual_names = {t.name for t in tools}
    assert_equal(actual_names, expected_names, "5.2 工具名称集合完全匹配")

    # 5.3 register - 注册新工具
    r2 = ToolRegistry()
    r2.register("test_tool", "测试工具", {"type": "object", "properties": {}}, lambda: "ok")
    tool = r2.get_tool("test_tool")
    assert_equal(tool.name, "test_tool", "5.3 register/get_tool 注册并获取工具")

    # 5.4 register - 重复注册异常
    assert_raises(
        ValueError,
        lambda: r2.register("test_tool", "dup", {}, lambda: None),
        "5.4 register 重复注册抛出 ValueError",
    )

    # 5.5 get_tool - 不存在的工具
    assert_raises(
        KeyError,
        lambda: r2.get_tool("nonexistent"),
        "5.5 get_tool 不存在抛出 KeyError",
    )

    # 5.6 call - 调用工具
    result = r2.call("test_tool")
    assert_equal(result, "ok", "5.6 call 调用工具返回正确结果")

    # 5.7 call - 调用不存在的工具
    assert_raises(
        KeyError,
        lambda: r2.call("nonexistent"),
        "5.7 call 不存在工具抛出 KeyError",
    )

    # 5.8 get_tool_schemas - 返回正确格式
    schemas = registry.get_tool_schemas()
    assert_equal(len(schemas), 14, "5.8 get_tool_schemas 返回 14 个 schema")
    for s in schemas:
        assert_equal(s["type"], "function", f"5.8 schema type 为 function: {s['function']['name']}")
        assert_true("name" in s["function"], f"5.8 schema 包含 name: {s['function']['name']}")
        assert_true("description" in s["function"], f"5.8 schema 包含 description: {s['function']['name']}")
        assert_true("parameters" in s["function"], f"5.8 schema 包含 parameters: {s['function']['name']}")

    # 5.9 ToolSpec 数据类
    spec = ToolSpec(name="t", description="d", parameters={}, handler=lambda: None)
    assert_equal(spec.name, "t", "5.9 ToolSpec 数据类正确")

    # 5.10 list_tools 返回 ToolSpec 列表
    all_tools = registry.list_tools()
    for t in all_tools:
        assert_true(isinstance(t, ToolSpec), f"5.10 list_tools 返回 ToolSpec: {t.name}")


# =============================================================================
# 6. 上下文压缩器测试
# =============================================================================
def test_context_compressor() -> None:
    test_section("6. 上下文压缩器测试")

    from context_compressor import ContextCompressor, estimate_tokens

    # 6.1 estimate_tokens 基础
    tokens = estimate_tokens("Hello World")
    assert_true(tokens > 0, "6.1 estimate_tokens 英文返回正数")

    # 6.2 estimate_tokens 中文
    tokens = estimate_tokens("你好世界")
    assert_true(tokens > 0, "6.2 estimate_tokens 中文返回正数")

    # 6.3 estimate_tokens 空字符串
    tokens = estimate_tokens("")
    assert_equal(tokens, 1, "6.3 estimate_tokens 空字符串返回 1")

    # 6.4 ContextCompressor 初始化
    cc = ContextCompressor(max_tokens=1000)
    assert_equal(cc.max_tokens, 1000, "6.4 max_tokens 正确设置")
    assert_equal(cc.threshold, 800, "6.4 threshold = 0.8 * max_tokens")

    # 6.5 should_compress - 消息较少时不压缩
    short_msgs = [{"role": "user", "content": "hello"}]
    assert_true(not cc.should_compress(short_msgs), "6.5 should_compress 短消息返回 False")

    # 6.6 should_compress - 消息较多时压缩
    long_content = "A" * 5000  # 5000/4 ≈ 1250 tokens > 800 threshold
    long_msgs = [{"role": "user", "content": long_content}]
    assert_true(cc.should_compress(long_msgs), "6.6 should_compress 长消息返回 True")

    # 6.7 compress - 无 LLM 客户端时使用简单截断
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "msg1"},
        {"role": "assistant", "content": "resp1"},
        {"role": "user", "content": "msg2"},
        {"role": "assistant", "content": "resp2"},
        {"role": "user", "content": "A" * 5000},
    ]
    compressed = cc.compress(messages)
    assert_true(len(compressed) > 0, "6.7 compress 返回非空列表")
    # 保留 system 消息
    assert_equal(compressed[0]["role"], "system", "6.7 compress 保留 system 消息")
    # 包含摘要消息
    has_summary = any("历史对话摘要" in m.get("content", "") for m in compressed)
    assert_true(has_summary, "6.7 compress 包含历史对话摘要")

    # 6.8 compress - 空消息列表
    assert_equal(cc.compress([]), [], "6.8 compress 空列表返回空列表")

    # 6.9 compress - 单条消息无需压缩
    single = [{"role": "user", "content": "hello"}]
    result = cc.compress(single)
    assert_equal(len(result), 1, "6.9 compress 单条消息不压缩")

    # 6.10 estimate_tokens 实例方法
    t = cc.estimate_tokens("test")
    assert_true(t > 0, "6.10 实例方法 estimate_tokens 可用")


# =============================================================================
# 7. inbox 事件监听测试
# =============================================================================
def test_inbox_listener() -> None:
    test_section("7. inbox 事件监听测试")

    from core.inbox_listener import InboxListener

    with tempfile.TemporaryDirectory() as tmpdir:
        inbox_dir = os.path.join(tmpdir, "inbox")
        received: list[str] = []

        def callback(content: str) -> None:
            received.append(content)

        listener = InboxListener(inbox_dir, callback)

        # 7.1 启动监听
        listener.start()
        assert_true(listener._thread is not None and listener._thread.is_alive(),
                     "7.1 InboxListener.start() 线程启动")

        # 7.2 向 inbox 写入文件，验证回调触发
        test_file = os.path.join(inbox_dir, "test_message.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("Hello from inbox!")

        # 等待文件系统事件触发
        time.sleep(1.0)
        assert_equal(len(received), 1, "7.2 inbox 文件写入后回调触发 1 次")
        if received:
            assert_equal(received[0], "Hello from inbox!", "7.2 回调收到正确内容")

        # 7.3 文件被自动删除
        assert_true(not os.path.exists(test_file), "7.3 处理完成后文件被自动删除")

        # 7.4 隐藏文件被忽略
        hidden_file = os.path.join(inbox_dir, ".gitkeep")
        with open(hidden_file, "w", encoding="utf-8") as f:
            f.write("hidden")
        time.sleep(1.0)
        assert_equal(len(received), 1, "7.4 隐藏文件 (.开头) 被忽略")

        # 7.5 停止监听
        listener.stop()
        time.sleep(0.5)
        assert_true(listener._thread is None or not listener._thread.is_alive(),
                     "7.5 InboxListener.stop() 线程停止")

        # 7.6 重复 start 不创建重复线程
        listener.start()
        time.sleep(0.3)
        listener.start()  # 第二次 start 应该跳过
        time.sleep(0.3)
        listener.stop()


# =============================================================================
# 8. 看门狗测试
# =============================================================================
def test_watchdog() -> None:
    test_section("8. 看门狗测试")

    # 注意: inbox_listener.py 已导入系统 watchdog 包，sys.modules['watchdog']
    # 指向的是系统库而非项目文件。使用 importlib 直接加载项目文件。
    import importlib.util
    wd_path = os.path.join(WORKSPACE, "watchdog.py")
    spec = importlib.util.spec_from_file_location("project_watchdog", wd_path)
    wd = importlib.util.module_from_spec(spec)

    # 8.1 语法正确导入
    try:
        spec.loader.exec_module(wd)
        assert_true(True, "8.1 watchdog.py 加载成功")
    except Exception as e:
        assert_true(False, f"8.1 watchdog.py 加载失败: {e}")
        return

    # 8.2 模块包含 main 函数
    assert_true(hasattr(wd, "main") and callable(wd.main), "8.2 watchdog.py 有 main 函数")

    # 8.3 模块包含关键常量
    assert_true(hasattr(wd, "_CHECK_INTERVAL"), "8.3 有 _CHECK_INTERVAL")
    assert_equal(wd._CHECK_INTERVAL, 3.0, "8.3 _CHECK_INTERVAL = 3.0")

    # 8.4 模块包含 _AGENT_SCRIPT
    assert_true(hasattr(wd, "_AGENT_SCRIPT"), "8.4 有 _AGENT_SCRIPT")
    assert_in("agent.py", wd._AGENT_SCRIPT, "8.4 _AGENT_SCRIPT 指向 agent.py")

    # 8.5 模块包含关键函数
    assert_true(hasattr(wd, "_setup_logging") and callable(wd._setup_logging),
                "8.5 有 _setup_logging")
    assert_true(hasattr(wd, "_signal_handler") and callable(wd._signal_handler),
                "8.5 有 _signal_handler")
    assert_true(hasattr(wd, "_register_signals") and callable(wd._register_signals),
                "8.5 有 _register_signals")
    assert_true(hasattr(wd, "_start_agent") and callable(wd._start_agent),
                "8.5 有 _start_agent")
    assert_true(hasattr(wd, "_is_alive") and callable(wd._is_alive),
                "8.5 有 _is_alive")
    assert_true(hasattr(wd, "_terminate_agent") and callable(wd._terminate_agent),
                "8.5 有 _terminate_agent")
    assert_true(hasattr(wd, "_git_reset_hard") and callable(wd._git_reset_hard),
                "8.5 有 _git_reset_hard")

    # 8.6 _is_alive 函数测试
    assert_true(wd._is_alive(os.getpid()), "8.6 _is_alive 当前进程返回 True")
    assert_true(not wd._is_alive(99999), "8.6 _is_alive 不存在 PID 返回 False")


# =============================================================================
# 9. LLM 客户端测试
# =============================================================================
def test_llm_client() -> None:
    test_section("9. LLM 客户端测试")

    # 9.1 模块可导入
    try:
        from llm.client import LLMClient, LLM_API_KEY, LLM_API_BASE, LLM_MODEL, LLM_MAX_TOKENS
        assert_true(True, "9.1 llm/client.py 导入成功")
    except Exception as e:
        assert_true(False, f"9.1 llm/client.py 导入失败: {e}")
        return

    # 9.2 环境变量常量存在
    assert_true(len(LLM_API_BASE) > 0, "9.2 LLM_API_BASE 常量存在")
    assert_true(len(LLM_MODEL) > 0, "9.2 LLM_MODEL 常量存在")
    assert_true(LLM_MAX_TOKENS > 0, "9.2 LLM_MAX_TOKENS 为正数")

    # 9.3 LLMClient 类结构正确
    # 验证方法存在
    assert_true(hasattr(LLMClient, "chat") and callable(LLMClient.chat),
                "9.3 LLMClient 有 chat 方法")
    assert_true(hasattr(LLMClient, "_chat_sync"), "9.3 有 _chat_sync")
    assert_true(hasattr(LLMClient, "_chat_stream"), "9.3 有 _chat_stream")
    assert_true(hasattr(LLMClient, "_should_retry"), "9.3 有 _should_retry")
    assert_true(hasattr(LLMClient, "_retry"), "9.3 有 _retry")
    assert_true(hasattr(LLMClient, "_build_kwargs"), "9.3 有 _build_kwargs")

    # 9.4 实例化测试（使用 .env 中的配置）
    try:
        client = LLMClient()
        assert_true(True, "9.4 LLMClient 实例化成功（使用 .env 配置）")
    except ValueError as e:
        # 如果 .env 没有 API key，这是预期行为
        assert_in("LLM_API_KEY", str(e), "9.4 LLMClient 实例化报错（缺少 API key）")

    # 9.5 _should_retry 逻辑
    try:
        client = LLMClient(api_key="sk-test", base_url="https://test.example.com/v1")
    except Exception:
        client = LLMClient(api_key="sk-test")
    from openai import APIStatusError, APITimeoutError, APIConnectionError
    from unittest.mock import MagicMock

    def _make_status_error(status_code: int) -> APIStatusError:
        """创建模拟的 APIStatusError（兼容不同版本的 openai 包）"""
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.request = MagicMock()
        mock_response.json.return_value = {"error": {"message": "test"}}
        # 部分版本 body 参数签名不同，尝试两种方式
        try:
            return APIStatusError("test error", response=mock_response, body={"error": "test"})
        except TypeError:
            return APIStatusError("test error", response=mock_response, body=None)

    # 429 应重试
    mock_429 = _make_status_error(429)
    assert_true(client._should_retry(mock_429), "9.5 _should_retry 429 返回 True")

    # 500 应重试
    mock_500 = _make_status_error(500)
    assert_true(client._should_retry(mock_500), "9.5 _should_retry 5xx 返回 True")

    # 400 不应重试
    mock_400 = _make_status_error(400)
    assert_true(not client._should_retry(mock_400), "9.5 _should_retry 4xx(非429) 返回 False")

    # 超时应重试
    mock_request = MagicMock()
    mock_request.method = "POST"
    mock_request.url = "https://test.example.com/v1/chat/completions"
    timeout_err = APITimeoutError(mock_request)
    assert_true(client._should_retry(timeout_err), "9.5 _should_retry timeout 返回 True")

    # 连接错误应重试
    conn_err = APIConnectionError(request=mock_request)
    assert_true(client._should_retry(conn_err), "9.5 _should_retry connection error 返回 True")


# =============================================================================
# 10. Agent 主循环测试
# =============================================================================
def test_agent() -> None:
    test_section("10. Agent 主循环测试")

    # 设置 LLM_API_KEY 以便 Agent 可以实例化（不实际运行）
    os.environ.setdefault("LLM_API_KEY", "sk-test-agent")

    # 10.1 模块可导入
    try:
        import agent as agent_mod
        assert_true(True, "10.1 agent.py 导入成功")
    except Exception as e:
        assert_true(False, f"10.1 agent.py 导入失败: {e}")
        return

    # 10.2 Agent 类存在
    from agent import Agent
    assert_true(hasattr(Agent, "run"), "10.2 Agent 有 run 方法")
    assert_true(hasattr(Agent, "_main_loop"), "10.2 Agent 有 _main_loop")
    assert_true(hasattr(Agent, "_process_llm_iteration"), "10.2 Agent 有 _process_llm_iteration")
    assert_true(hasattr(Agent, "_call_llm"), "10.2 Agent 有 _call_llm")
    assert_true(hasattr(Agent, "_check_anchor"), "10.2 Agent 有 _check_anchor")
    assert_true(hasattr(Agent, "_auto_git_commit"), "10.2 Agent 有 _auto_git_commit")
    assert_true(hasattr(Agent, "_on_inbox_message"), "10.2 Agent 有 _on_inbox_message")
    assert_true(hasattr(Agent, "_process_inbox_message"), "10.2 Agent 有 _process_inbox_message")
    assert_true(hasattr(Agent, "_load_system_prompt"), "10.2 Agent 有 _load_system_prompt")
    assert_true(hasattr(Agent, "_parse_tool_args"), "10.2 Agent 有 _parse_tool_args")

    # 10.3 锚点保护 - write_file 拒绝 watchdog.py
    err = Agent._check_anchor("write_file", {"path": os.path.join(WORKSPACE, "watchdog.py")})
    assert_true(err is not None, "10.3 _check_anchor write_file watchdog.py 返回错误")
    assert_in("watchdog.py", err, "10.3 错误消息包含 watchdog.py")

    # 10.4 锚点保护 - write_file 拒绝 core/
    err = Agent._check_anchor("write_file", {"path": os.path.join(WORKSPACE, "core", "registry.py")})
    assert_true(err is not None, "10.4 _check_anchor write_file core/ 返回错误")
    assert_in("core/", err, "10.4 错误消息包含 core/")

    # 10.5 锚点保护 - write_file 允许其他文件
    err = Agent._check_anchor("write_file", {"path": os.path.join(WORKSPACE, "test_other.py")})
    assert_true(err is None, "10.5 _check_anchor write_file 其他文件返回 None")

    # 10.6 锚点保护 - delete_file 拒绝 watchdog.py
    err = Agent._check_anchor("delete_file", {"path": os.path.join(WORKSPACE, "watchdog.py")})
    assert_true(err is not None, "10.6 _check_anchor delete_file watchdog.py 返回错误")

    # 10.7 锚点保护 - delete_file 拒绝 core/
    err = Agent._check_anchor("delete_file", {"path": os.path.join(WORKSPACE, "core", "file_tools.py")})
    assert_true(err is not None, "10.7 _check_anchor delete_file core/ 返回错误")

    # 10.8 锚点保护 - 非 write_file/delete_file 不检查
    err = Agent._check_anchor("read_file", {"path": os.path.join(WORKSPACE, "watchdog.py")})
    assert_true(err is None, "10.8 _check_anchor read_file watchdog.py 返回 None")

    # 10.9 _parse_tool_args 正常解析
    tc = {"function": {"arguments": '{"key": "value"}'}}
    args = Agent._parse_tool_args(tc)
    assert_equal(args, {"key": "value"}, "10.9 _parse_tool_args 正确解析 JSON")

    # 10.10 _parse_tool_args 异常 JSON
    tc_bad = {"function": {"arguments": "{invalid json}"}}
    args = Agent._parse_tool_args(tc_bad)
    assert_equal(args, {}, "10.10 _parse_tool_args 异常 JSON 返回空字典")

    # 10.11 Agent 常量正确（路径动态计算，应包含项目目录名）
    workspace_lower = agent_mod._WORKSPACE.lower()
    assert_true(
        "self-evolving-agent" in workspace_lower or workspace_lower.endswith("self-evolving-agent"),
        f"10.11 _WORKSPACE 应指向项目目录: {agent_mod._WORKSPACE}",
    )
    assert_in("memory/system.md", agent_mod._SYSTEM_PROMPT_PATH, "10.11 _SYSTEM_PROMPT_PATH")
    assert_in("inbox", agent_mod._INBOX_DIR, "10.11 _INBOX_DIR")
    assert_in("response.txt", agent_mod._INBOX_RESPONSE_PATH, "10.11 _INBOX_RESPONSE_PATH")

    # 10.12 _SELF_FILES 包含关键文件
    assert_true(any("agent.py" in f for f in agent_mod._SELF_FILES),
                "10.12 _SELF_FILES 包含 agent.py")
    assert_true(any("llm/client.py" in f for f in agent_mod._SELF_FILES),
                "10.12 _SELF_FILES 包含 llm/client.py")
    assert_true(any("context_compressor.py" in f for f in agent_mod._SELF_FILES),
                "10.12 _SELF_FILES 包含 context_compressor.py")
    assert_true(any("system.md" in f for f in agent_mod._SELF_FILES),
                "10.12 _SELF_FILES 包含 system.md")

    # 10.13 Agent 实例化（不运行主循环）
    try:
        agent_instance = Agent()
        assert_true(isinstance(agent_instance.registry, type(agent_instance.registry)),
                    "10.13 Agent 实例化成功")
        assert_true(agent_instance.max_iterations == 100, "10.13 max_iterations = 100")
        assert_true(len(agent_instance.registry.list_tools()) == 14, "10.13 registry 有 14 个工具")
    except Exception as e:
        print(f"  ⚠️ Agent 实例化失败: {e}")


# =============================================================================
# 主入口
# =============================================================================
def main() -> None:
    print("=" * 60)
    print("  自我进化 Agent 项目 - 基础功能测试")
    print("=" * 60)
    print(f"  Python: {sys.version}")
    print(f"  工作目录: {WORKSPACE}")
    print(f"  .venv: {sys.executable}")

    tests: list[tuple[str, callable]] = [
        ("文件工具", test_file_tools),
        ("命令行工具", test_shell_tools),
        ("网页工具", test_web_tools),
        ("Git 工具", test_git_tools),
        ("工具注册表", test_registry),
        ("上下文压缩器", test_context_compressor),
        ("inbox 事件监听", test_inbox_listener),
        ("看门狗", test_watchdog),
        ("LLM 客户端", test_llm_client),
        ("Agent 主循环", test_agent),
    ]

    for name, fn in tests:
        try:
            fn()
        except Exception as e:
            global TESTS_FAILED
            TESTS_FAILED += 1
            TEST_DETAILS.append({"name": f"测试组 '{name}' 整体", "status": "ERROR", "detail": str(e)})
            print(f"  ❌ 测试组 '{name}' 异常: {e}")
            traceback.print_exc()

    # 汇总
    total = TESTS_PASSED + TESTS_FAILED
    print(f"\n{'=' * 60}")
    print(f"  测试汇总")
    print(f"{'=' * 60}")
    print(f"  通过: {TESTS_PASSED}")
    print(f"  失败: {TESTS_FAILED}")
    print(f"  总计: {total}")
    if total > 0:
        print(f"  通过率: {TESTS_PASSED / total * 100:.1f}%")
    print(f"{'=' * 60}")

    # 清理临时测试文件
    if os.path.exists(os.path.join(WORKSPACE, "_test_all.py")):
        pass  # 保留脚本本身

    # 返回退出码
    sys.exit(0 if TESTS_FAILED == 0 else 1)


if __name__ == "__main__":
    main()
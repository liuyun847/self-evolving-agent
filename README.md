# Self-Evolving-Agent

基于 LLM 驱动的**自我进化 AI Agent**。Agent 拥有文件读写、命令行执行、网页搜索等基础能力，通过调用 LLM API 持续读写和修改自身源代码来扩展能力、修复缺陷、优化性能。

> ⚠️ **安全警告**：此 Agent 拥有完整的 shell 执行权限和文件系统读写权限，能自行修改代码。**强烈建议只在隔离环境（虚拟机或容器）中运行**，切勿在宿主机或生产环境中直接运行，以免造成不可逆的数据损失或安全风险。

## 特性

- **自我进化**：Agent 能自主分析现有代码，编写改进并应用，无需人工干预
- **事件驱动架构**：统一的 `queue.Queue` 事件循环，支持 LLM 迭代和外部消息混合调度
- **工具集**：内置 14 个工具，覆盖文件操作、命令行执行、网页搜索、Git 版本控制
- **看门狗机制**：`watchdog.py` 监控 Agent 进程存活，崩溃后自动 `git reset --hard` 并重启
- **上下文压缩**：当对话 token 接近上限时自动压缩历史消息，避免上下文溢出
- **锚点保护**：禁止 Agent 修改 `watchdog.py` 和 `core/` 等核心文件，防止自毁
- **inbox 外部通信**：外部进程可通过 `inbox` 目录向 Agent 发送消息，响应写入 `inbox/response.txt`
- **自动版本控制**：每次文件操作后自动 `git add` + `git commit`
- **自我重启**：检测到自身源码修改后自动退出，触发看门狗重启使新代码生效

## 项目结构

```
Self-Evolving-Agent/
├── agent.py                # Agent 主循环（事件驱动、LLM 调用、工具执行）
├── watchdog.py             # 看门狗（进程监控、崩溃恢复、自动重启）
├── context_compressor.py   # 上下文压缩器（token 估算、历史摘要）
├── _test_all.py            # 综合测试脚本（10 个测试组）
├── pyproject.toml          # 项目配置与依赖
├── README.md
├── .gitignore
├── memory/
│   └── system.md           # 系统提示词（定义 Agent 行为准则与可用工具）
├── inbox/
│   └── .gitkeep            # 外部消息投递目录
├── llm/
│   ├── __init__.py
│   └── client.py           # LLM 客户端（OpenAI 兼容 API、指数退避重试）
└── core/                   # 核心工具集（只读锚点，不可被 Agent 修改）
    ├── __init__.py         # 工具注册表工厂函数
    ├── registry.py         # 工具注册表（ToolRegistry / ToolSpec）
    ├── file_tools.py       # 文件工具（读写、追加、列表、删除）
    ├── shell_tools.py      # 命令行工具（subprocess 封装）
    ├── web_tools.py        # 网页工具（DuckDuckGo 搜索、网页抓取）
    ├── git_tools.py        # Git 工具（status/add/commit/diff/log/reset）
    └── inbox_listener.py   # inbox 文件系统事件监听
```

## 架构概览

```
                   ┌──────────┐
                   │ watchdog │  ← 监控 agent 进程，崩溃后 git reset 并重启
                   └────┬─────┘
                        │ 启动/重启
        ┌───────────────▼───────────────┐
        │           agent.py            │
        │  ┌─────────────────────────┐  │
        │  │     事件驱动主循环       │  │
        │  │  ┌──────┐  ┌──────────┐ │  │
        │  │  │ LLM  │  │  inbox   │ │  │
        │  │  │ 迭代 │  │  消息    │ │  │
        │  │  └──┬───┘  └────┬─────┘ │  │
        │  │     └─────┬──────┘       │  │
        │  │           ▼              │  │
        │  │   ┌──────────────┐       │  │
        │  │   │ ToolRegistry │       │  │
        │  │   │  (14 tools)  │       │  │
        │  │   └──────┬───────┘       │  │
        │  │   ┌──────┼──────┐        │  │
        │  │   ▼      ▼      ▼        │  │
        │  │ file  shell   web/git    │  │
        │  └─────────────────────────┘  │
        │  ┌─────────────────────────┐  │
        │  │   ContextCompressor     │  │
        │  │   (token 监控 + 压缩)    │  │
        │  └─────────────────────────┘  │
        │  ┌─────────────────────────┐  │
        │  │   锚点保护              │  │
        │  │   (watchdog.py ❌       │  │
        │  │    core/      ❌)       │  │
        │  └─────────────────────────┘  │
        └───────────────────────────────┘
```

## 运行流程

1. **启动**：`watchdog.py` 启动 `agent.py` 子进程
2. **初始化**：加载 `memory/system.md` 作为系统提示词 → 检查 Git 工作区 → 启动 inbox 监听
3. **主循环**：LLM 迭代 → 解析 `tool_calls` → 锚点检查 → 执行工具 → 回写结果 → 自动 Git commit
4. **自我进化**：Agent 修改自身代码 → 检测到 `_SELF_FILES` 中文件被修改 → `sys.exit(0)` → 看门狗重启
5. **崩溃恢复**：Agent 进程异常退出 → 看门狗 `git reset --hard HEAD` → 重新启动

## 环境要求

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) 包管理器
- Git
- LLM API (OpenAI 兼容接口，如 GPT-4 / Claude 等)
- 推荐运行环境：Linux 虚拟机

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-username/self-evolving-agent.git
cd self-evolving-agent
```

### 2. 安装依赖

```bash
uv sync
```

### 3. 配置环境变量

创建 `.env` 文件（已加入 `.gitignore`）：

```env
LLM_API_KEY=your-api-key
LLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4
LLM_MAX_TOKENS=128000
```

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `LLM_API_KEY` | API 密钥（必填） | - |
| `LLM_API_BASE` | API 基础 URL | `https://api.openai.com/v1` |
| `LLM_MODEL` | 模型名称 | `gpt-4` |
| `LLM_MAX_TOKENS` | 最大上下文 token | `128000` |

### 4. 自定义系统提示词（可选）

编辑 `memory/system.md`，定义 Agent 的行为准则、可用工具和初始任务。

### 5. 运行

```bash
# 直接运行 Agent（调试模式）
uv run python agent.py

# 通过看门狗运行（生产模式，崩溃自动恢复）
uv run python watchdog.py
```

### 6. 向 Agent 发送消息

将文本文件放入 `inbox/` 目录即可，Agent 处理后会删除文件并将响应写入 `inbox/response.txt`：

```bash
echo "你的消息" > inbox/message.txt
cat inbox/response.txt
```

### 7. 运行测试

```bash
uv run python _test_all.py
```

## 工具列表

### 文件操作

| 工具 | 说明 |
|------|------|
| `read_file` | 读取文件内容 |
| `write_file` | 写入文件（覆盖模式，自动创建父目录） |
| `append_file` | 追加内容到文件末尾 |
| `list_dir` | 列出目录内容 |
| `delete_file` | 删除文件 |

### 命令行

| 工具 | 说明 |
|------|------|
| `run_command` | 执行 shell 命令（支持超时控制） |

### 网页

| 工具 | 说明 |
|------|------|
| `web_search` | DuckDuckGo 网页搜索 |
| `web_fetch` | 抓取网页并提取纯文本 |

### Git 版本控制

| 工具 | 说明 |
|------|------|
| `git_status` | 查看工作区状态 |
| `git_add` | 添加文件到暂存区 |
| `git_commit` | 提交暂存的变更 |
| `git_diff` | 查看工作区差异 |
| `git_log` | 查看提交历史 |
| `git_reset` | 重置（soft/hard） |

## 安全机制

### 锚点保护

以下文件和目录对 Agent **只读**，任何写入/删除操作都会被拦截：

| 文件/目录 | 说明 |
|-----------|------|
| `watchdog.py` | 看门狗进程，不可修改 |
| `core/` 目录 | 核心工具集，不可修改 |

### 崩溃恢复

看门狗每 3 秒检测一次 Agent 进程存活。若进程死亡：
1. 收集 Agent 最后的 stdout/stderr 输出
2. 执行 `git reset --hard HEAD` 回滚所有未提交变更
3. 重新启动 Agent

### 优雅退出

看门狗处理 `SIGTERM` / `SIGINT` 信号，收到后先尝试 `SIGTERM` 优雅终止 Agent，等待 5 秒未响应则发送 `SIGKILL`。

## LLM 客户端特性

- **指数退避重试**：自动重试 429 / 5xx / 超时 / 连接错误，重试间隔 1s → 2s → 4s → 8s
- **流式 + 非流式**：同时支持流式和非流式响应
- **OpenAI 兼容**：兼容任何 OpenAI API 格式的 LLM 服务（如 DeepSeek、Claude 等）
- **.env 配置**：通过环境变量灵活配置，无需修改代码

## 上下文压缩

当消息列表的预估 token 数超过 `MAX_TOKENS * 0.8`（默认 102400）时自动压缩：

- 保留 `system` 消息
- 保留最近的 N 条消息（不超过阈值）
- 将中间的旧消息替换为总结摘要
- 支持 LLM 摘要（有 LLM 客户端时）和简单截断两种模式

## 部署到虚拟机

推荐部署到 Linux 虚拟机运行。典型部署流程：

1. 将项目克隆到虚拟机 `/home/agent/self-evolving-agent`
2. 配置 `.env` 文件
3. 使用 tmux 后台运行：`tmux new-session -d -s agent 'cd ~/self-evolving-agent && uv run python watchdog.py'`

## 注意事项

1. **API 密钥安全**：`.env` 文件已加入 `.gitignore`，切勿提交到版本控制
2. **沙箱运行**：Agent 拥有完整的 shell 执行权限，请在隔离环境（虚拟机/容器）中运行
3. **Git 依赖**：项目依赖 Git 进行版本控制和崩溃恢复，请确保 Git 已安装
4. **不修改核心文件**：Agent 受到锚点保护，无法修改 `watchdog.py` 和 `core/` 目录

## 许可证

MIT
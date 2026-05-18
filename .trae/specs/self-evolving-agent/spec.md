# 自我进化 Agent 设计文档

**日期**: 2026-05-17
**状态**: 已批准

## Why

实验性质的 Agent 项目，通过调用 LLM API，利用文件读写、命令行执行、网页搜索和网页捕获等基础能力，读写自身源代码来持续扩展能力。运行在配置严格的虚拟机环境中，拥有完整权限。

## What Changes

- 初始化 Python 项目结构（uv 管理依赖）
- 实现核心工具集（文件、命令行、网页、git），通过统一注册表暴露给 LLM
- 实现 LLM 客户端（OpenAI 兼容 API + 重试机制）
- 实现上下文压缩器（token 估算 + 摘要压缩）
- 实现 Agent 主循环（事件驱动、动作解析、自我重启）
- 实现看门狗进程（PID 监控 + git reset + 重启）
- 实现 inbox 事件监听（文件系统事件驱动）
- 编写初始提示词 `memory/system.md`

## Impact

- Affected specs: 无（全新项目）
- Affected code: 全新项目，涉及 agent.py、watchdog.py、core/、llm/、context_compressor.py、memory/system.md

## ADDED Requirements

### Requirement: 项目骨架初始化

系统 SHALL 提供完整的 Python 项目结构，使用 uv 管理依赖，git 管理版本。

#### Scenario: 项目初始化成功
- **WHEN** 执行初始化脚本
- **THEN** 创建完整目录结构、.gitignore、.env 模板、pyproject.toml

---

### Requirement: 核心工具集 (core/)

系统 SHALL 提供可复用的基础工具集，所有工具通过统一注册表暴露，core/ 目录为只读锚点不可被 Agent 修改。

#### Scenario: 文件工具 - 读写文件
- **WHEN** Agent 调用 file_tools 读写文件
- **THEN** 正确读写指定路径的文件内容，支持读、写、追加、列表目录、删除操作

#### Scenario: 命令行工具 - 执行命令
- **WHEN** Agent 调用 shell_tools 执行命令
- **THEN** 在指定超时和环境变量下执行命令，返回 stdout/stderr 和退出码

#### Scenario: 网页工具 - 搜索与捕获
- **WHEN** Agent 调用 web_tools 搜索网页或捕获网页内容
- **THEN** 返回搜索结果列表，或将 HTML 页面转换为纯文本返回

#### Scenario: Git 工具 - 版本控制
- **WHEN** Agent 调用 git_tools 执行 git 操作
- **THEN** 正确执行 git status/add/commit/diff/log/reset 操作

#### Scenario: 工具注册表 - 统一接口
- **WHEN** 通过 registry 注册和查询工具
- **THEN** 返回工具列表及调用规范，支持统一调用接口

---

### Requirement: LLM 客户端 (llm/client.py)

系统 SHALL 提供 OpenAI 兼容 API 调用能力，包含重试机制，支持流式和非流式响应。

#### Scenario: 正常 API 调用
- **WHEN** Agent 调用 LLM API
- **THEN** 发送请求并返回模型响应

#### Scenario: API 调用失败重试
- **WHEN** API 调用返回可重试错误（如 429、5xx）
- **THEN** 按指数退避策略自动重试，最多 N 次（可配置）

#### Scenario: 流式响应
- **WHEN** 启用流式模式
- **THEN** 逐 token 返回响应内容

---

### Requirement: 上下文压缩器 (context_compressor.py)

系统 SHALL 在上下文 token 数超过 API 限制的 80% 时触发摘要压缩。

#### Scenario: 上下文超阈值触发压缩
- **WHEN** 上下文 token 数超过限制的 80%
- **THEN** 将旧内容摘要化后作为上下文返回，不落盘

#### Scenario: 上下文未超阈值
- **WHEN** 上下文 token 数低于限制的 80%
- **THEN** 不做任何处理，原样返回

---

### Requirement: 初始提示词 (memory/system.md)

系统 SHALL 提供初始提示词，定义 Agent 身份、目标、可用工具和运行环境。

#### Scenario: 加载初始提示词
- **WHEN** Agent 启动
- **THEN** 读取 memory/system.md 作为系统提示词组装请求

---

### Requirement: Agent 主循环 (agent.py)

系统 SHALL 实现事件驱动的主循环，从队列获取任务，组装上下文调用 LLM，解析并执行动作。

#### Scenario: LLM 循环迭代
- **WHEN** Agent 主循环运行
- **THEN** 每轮迭代：组装上下文 → 调用 LLM → 解析动作 → 执行 → 结果回写上下文 → 压缩判断 → 下一轮

#### Scenario: 动作解析 - 工具调用
- **WHEN** LLM 返回工具调用请求
- **THEN** 解析工具名和参数，通过 registry 调用对应工具，结果回写上下文

#### Scenario: 动作解析 - 文件写入
- **WHEN** LLM 返回文件写入请求
- **THEN** 写入指定文件，执行 git commit

#### Scenario: 自我重启
- **WHEN** Agent 修改自身源码后需要重启
- **THEN** 通过 exec 替换进程或退出触发看门狗重启

---

### Requirement: 事件监听线程 (agent.py 内)

系统 SHALL 提供独立线程监听 inbox/ 目录变化，使用文件系统事件而非轮询。

#### Scenario: inbox 新文件事件
- **WHEN** 外部程序写入文件到 inbox/ 目录
- **THEN** 事件监听线程检测到变化，读取文件内容，推入主循环队列，删除/归档文件

---

### Requirement: 看门狗 (watchdog.py)

系统 SHALL 提供看门狗进程，监控 agent 进程 PID 存活，失能时执行 git reset --hard 并重启。

#### Scenario: Agent 进程存活
- **WHEN** 看门狗检测到 agent PID 存在
- **THEN** 不做任何操作，继续监控

#### Scenario: Agent 进程死亡
- **WHEN** 看门狗检测到 agent PID 不存在
- **THEN** 执行 git reset --hard HEAD，重新启动 agent.py

---

### Requirement: 自我进化约束

系统 SHALL 限制 Agent 只能修改非锚点文件，watchdog.py 和 core/ 目录不可修改。

#### Scenario: 允许修改的文件
- **WHEN** Agent 尝试修改 agent.py、llm/client.py、context_compressor.py、memory/system.md
- **THEN** 操作成功执行

#### Scenario: 禁止修改的文件
- **WHEN** Agent 尝试修改 watchdog.py 或 core/ 下任何文件
- **THEN** 操作被拒绝

---

### Requirement: 环境约束

系统 SHALL 运行在 Python 3.12+ 环境，所有依赖通过 uv 管理，API Key 从 .env 文件读取。
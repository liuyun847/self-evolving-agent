# Tasks

## 阶段一：项目骨架

- [x] Task 1: 初始化项目结构
  - [x] 创建完整目录结构（core/、llm/、memory/、inbox/）
  - [x] `git init`，创建 `.gitignore`
  - [x] 创建 `.env` 文件（含 API Key 占位符）
  - [x] `uv init` 初始化 Python 项目，创建 `pyproject.toml`

- [x] Task 2: 实现核心工具集 - 工具注册表 (core/registry.py)
  - [x] 定义工具注册/查询/调用统一接口
  - [x] 支持工具描述暴露给 LLM（函数名、参数 schema、描述）

- [x] Task 3: 实现核心工具集 - 文件工具 (core/file_tools.py)
  - [x] 读文件、写文件、追加文件
  - [x] 列表目录、删除文件
  - [x] 通过 registry 注册

- [x] Task 4: 实现核心工具集 - 命令行工具 (core/shell_tools.py)
  - [x] 执行命令行命令
  - [x] 支持超时参数和环境变量
  - [x] 返回 stdout、stderr、退出码
  - [x] 通过 registry 注册

- [x] Task 5: 实现核心工具集 - 网页工具 (core/web_tools.py)
  - [x] 网页搜索（HTTP 请求搜索引擎或直接搜索）
  - [x] 网页内容捕获（fetch URL → HTML → 纯文本）
  - [x] 通过 registry 注册

- [x] Task 6: 实现核心工具集 - Git 工具 (core/git_tools.py)
  - [x] git status、add、commit、diff、log、reset
  - [x] 通过 registry 注册

- [x] Task 7: 实现 core/__init__.py
  - [x] 导出 registry 和所有工具模块

- [x] Task 8: 实现 LLM 客户端 (llm/client.py)
  - [x] OpenAI 兼容 API 调用
  - [x] 重试机制（指数退避，可配置重试次数）
  - [x] 流式/非流式响应支持
  - [x] API Key 从环境变量读取

- [x] Task 9: 实现上下文压缩器 (context_compressor.py)
  - [x] Token 估算（基于 tiktoken 或简单字符估算）
  - [x] 超阈值（API 限制 80%）触发摘要压缩
  - [x] 摘要结果返回给主循环，不落盘

- [x] Task 10: 编写初始提示词 (memory/system.md)
  - [x] Agent 身份定义
  - [x] 目标：通过读写自身源码持续增强能力
  - [x] 可用工具描述
  - [x] 运行环境说明（虚拟机/高权限/允许风险方案）
  - [x] 首个任务：API 重试机制

## 阶段二：Agent 与看门狗

- [x] Task 11: 实现 Agent 主循环 (agent.py)
  - [x] 事件队列 + 主循环框架
  - [x] 组装上下文（system.md + 对话历史 + 工具定义）
  - [x] 调用 LLM，解析响应
  - [x] 动作解析器：工具调用、文件写入、git 操作
  - [x] 结果回写上下文
  - [x] 上下文压缩判断
  - [x] 自我重启逻辑（exec 替换进程或 sys.exit）

- [x] Task 12: 实现 inbox 事件监听线程
  - [x] 独立线程监听 inbox/ 目录变化
  - [x] 使用 watchdog 库实现文件系统事件监听
  - [x] 新文件出现 → 读取内容 → 推入主循环队列 → 删除文件

- [x] Task 13: 实现看门狗 (watchdog.py)
  - [x] 启动 agent.py 子进程，记录 PID
  - [x] 循环检测 PID 存活
  - [x] 进程死亡 → git reset --hard HEAD → 重新启动 agent.py

## 阶段三：验证与测试

- [x] Task 14: 基础功能测试 (196/196 通过)
  - [x] 各工具独立功能测试
  - [x] LLM 客户端连通性测试
  - [x] 看门狗重启逻辑测试
  - [x] inbox 事件监听测试

- [x] Task 15: 集成验证 (53/53 通过)
  - [x] 完整启动流程验证
  - [x] Agent 完成首个任务（API 重试机制）验证
  - [x] 自我修改 + 重启恢复流程验证

# Task Dependencies

- Task 2 依赖 Task 1
- Task 3-6 依赖 Task 2
- Task 7 依赖 Task 3-6
- Task 8-10 依赖 Task 1
- Task 11 依赖 Task 2-10
- Task 12 依赖 Task 1
- Task 13 依赖 Task 1
- Task 14 依赖 Task 3-13
- Task 15 依赖 Task 14
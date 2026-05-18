# Checklist

## 项目骨架

- [x] 项目目录结构完整（core/、llm/、memory/、inbox/）
- [x] .gitignore 存在且包含合理的忽略规则
- [x] .env 文件存在且包含 API Key 占位符
- [x] pyproject.toml 存在且包含项目元数据和依赖
- [x] git 仓库已初始化

## 核心工具集

- [x] core/registry.py 提供工具注册/查询/调用统一接口
- [x] core/file_tools.py 实现读、写、追加、列表、删除功能
- [x] core/shell_tools.py 实现命令执行（超时、环境变量、返回 stdout/stderr/退出码）
- [x] core/web_tools.py 实现网页搜索和网页内容捕获
- [x] core/git_tools.py 实现 git status/add/commit/diff/log/reset
- [x] core/__init__.py 正确导出所有模块
- [x] 所有工具通过 registry 注册且可查询

## LLM 客户端

- [x] llm/client.py 实现 OpenAI 兼容 API 调用
- [x] 重试机制实现（指数退避、可配置次数）
- [x] 流式和非流式响应均支持
- [x] API Key 从环境变量 .env 读取

## 上下文压缩器

- [x] context_compressor.py 实现 token 估算
- [x] 超过 API 限制 80% 时触发摘要压缩
- [x] 压缩结果不落盘，仅返回给主循环

## 初始提示词

- [x] memory/system.md 包含 Agent 身份定义
- [x] 包含目标和可用工具描述
- [x] 包含运行环境说明
- [x] 包含首个任务说明

## Agent 主循环

- [x] agent.py 实现事件队列 + 主循环
- [x] 正确组装上下文（system.md + 对话历史 + 工具定义）
- [x] 动作解析器支持工具调用
- [x] 动作解析器支持文件写入 + git commit
- [x] 结果正确回写上下文
- [x] 上下文压缩判断逻辑正确
- [x] 自我重启逻辑正确（exec 替换或 sys.exit）

## 事件监听

- [x] inbox/ 目录变化监听使用文件系统事件（非轮询）
- [x] 新文件内容正确读取并推入主循环队列
- [x] 处理完成后文件被删除

## 看门狗

- [x] watchdog.py 正确启动 agent.py 子进程
- [x] 循环检测 PID 存活
- [x] 进程死亡时执行 git reset --hard HEAD
- [x] 进程死亡时重新启动 agent.py

## 自我进化约束

- [x] Agent 修改非锚点文件（agent.py、llm/、context_compressor.py、memory/）正常执行
- [x] Agent 尝试修改 watchdog.py 被拒绝
- [x] Agent 尝试修改 core/ 下文件被拒绝

## 测试验证

- [x] 各工具独立功能测试通过
- [x] LLM 客户端连通性测试通过
- [x] 看门狗重启逻辑测试通过
- [x] inbox 事件监听测试通过
- [x] 完整启动流程验证通过
- [x] 首个任务（API 重试机制）验证通过
- [x] 自我修改 + 重启恢复流程验证通过
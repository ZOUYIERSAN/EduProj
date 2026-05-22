# intelligent-prep-garden

当前仓库是**先搭骨架、后写实现**的 Monorepo。  
目标是先明确“模块边界 + 通信契约 + 数据流”，再逐步填充业务代码。


## 目录与内容填写指南

### `frontend-nextjs/`

这里放前端项目（Next.js/React）代码

- 页面路由、状态管理、组件库、与网关通信的 API 封装


### `gateway-rust/`

这里放 Rust 网关与业务主控代码。

- `Cargo.toml`：放依赖与编译配置（如 HTTP 框架、数据库、Redis、JWT）
- `src/main.rs`：放服务启动流程（配置加载、日志、连接池、路由注册、优雅退出）
- `src/handlers/`：放 HTTP / WebSocket 路由处理器（按业务域拆分）
- `src/models/`：放 PostgreSQL 数据模型、查询对象、仓储层定义
- `src/clients/`：放调用 `ai-engine-python` 的内部客户端（HTTP/gRPC）

### `ai-engine-python/`

这里放 AI 计算服务（仅内网调用，不直接给前端）。

- `requirements.txt`：放 Python 依赖（FastAPI、OR-Tools、Transformers、Neo4j、Redis 等）
- `Dockerfile`：放 AI 服务镜像构建逻辑
- `app/main.py`：放 FastAPI 入口、路由挂载、服务初始化
- `app/planner/`：放运筹优化逻辑
- `app/tutor/`：放 DPO 模型推理与流式输出逻辑
- `app/graph_rag/`：放 Neo4j 图谱游走与掌握度更新逻辑

### `shared-contracts/`

这里放跨模块统一契约，避免“口头协议”导致联调失败。

- `api_schema.json`：放 OpenAPI 定义（前端 <-> 网关、网关 <-> AI 服务）
- `protobuf/`：放 `.proto` 文件（后续切 gRPC 时使用）
- 建议补充：统一错误码、请求/响应示例、事件消息体 Schema

### `docker-compose.yml`

这里放本地基础设施编排（非业务代码）。

- 当前服务：PostgreSQL、Neo4j、Redis
- 后续可补：健康检查、持久化策略、网络隔离、环境变量模板

### `ARCHITECTURE_BACKEND.md`

这里放后端架构主文档（通信机制与职责边界）。

- 已覆盖场景：同步 CRUD、跨服务调用、流式对话、异步图谱更新
- 后续建议：补时序图、失败重试策略、幂等性与可观测性规范



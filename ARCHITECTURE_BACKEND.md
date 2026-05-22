# 后端与架构通信设计（骨架版）

> 本文档只定义后端模块划分、目录边界与数据流，不包含业务实现代码。

## 1) 后端模块职责

### `gateway-rust`

- 面向前端的唯一入口（HTTP/WebSocket）
- 负责 JWT 鉴权、业务编排、Postgres 数据持久化
- 通过内部调用（HTTP/gRPC）调度 `ai-engine-python`
- 通过 Redis 桥接异步任务与流式消息

### `ai-engine-python`

- 仅内网可见，不直接暴露给前端
- `planner`: OR-Tools 生成复习计划
- `tutor`: DPO 模型推理与苏格拉底反问生成
- `graph_rag`: 读写 Neo4j 并更新掌握概率

### 数据层

- PostgreSQL: 结构化业务数据
- Neo4j: 知识图谱与掌握度
- Redis: 缓存 + 异步消息队列

## 2) 通信模式约定

1. 同步请求：Frontend -> `gateway-rust` -> Postgres  
2. 跨服务同步调用：`gateway-rust` -> `ai-engine-python`  
3. 流式交互：Frontend <-> `gateway-rust`(WS) + Redis + `ai-engine-python`  
4. 静默异步事件：`gateway-rust` -> Redis Event -> `ai-engine-python` -> Neo4j

## 3) 演进策略

1. **Make it work**: 先在 Python 内把 AI + 图谱链路跑通  
2. **Make it right**: 再稳定契约、统一日志/监控、补全边界  
3. **Make it fast**: 最后引入 Rust 网关承载高并发与流式体验

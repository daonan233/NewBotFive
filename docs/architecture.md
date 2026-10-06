# 技术架构

## 设计基线

本项目以 AstrBot 4.28 稳定系列的公开接口为基线。AstrBot 已经提供模型 Provider、Agent 循环、工具调用、会话、图片消息、Token 统计、知识库与插件开关，因此这些通用能力不在业务插件中重写。NapCat 仅承担 QQ 客户端和 OneBot 11 协议适配。

```text
QQ 用户/群
    │
    ▼
NapCatQQ（OneBot 11 客户端）
    │ Reverse WebSocket: ws://astrbot:6199/ws
    ▼
AstrBot（消息路由、会话、LLM Provider、Agent、Tool Calling）
    │
    ├── 官方/内置能力：聊天、会话、模型、工具、图片、知识库
    ├── 自定义 Star 插件：提醒、群总结、统计、语录、群管理
    ├── PostgreSQL + pgvector：业务真相源、审计、向量
    ├── Redis：去重、限流、临时上下文、锁、任务状态
    └── OpenAI Compatible API：可替换模型服务
```

## 边界与职责

| 组件 | 职责 | 不承担 |
|---|---|---|
| NapCatQQ | 登录 QQ、收发消息、OneBot 11 | 业务逻辑、模型调用 |
| AstrBot | 唤醒、会话、Provider、Agent、插件生命周期 | 自定义业务数据模型 |
| 自定义插件 | 群业务、业务权限、领域服务 | 重写 AstrBot 的通用 Agent |
| PostgreSQL | 持久业务数据、提醒真相源、向量 | 高频临时计数 |
| Redis | 去重、限流、短期缓存、锁 | 唯一持久数据源 |

## 会话隔离

- 私聊：按 `平台 + private + user_id` 隔离。
- 群聊：在 AstrBot 配置中开启 `unique_session`，按 `平台 + group_id + user_id` 隔离。
- 业务表同时保留 `user_id` 和可空的 `group_id`；所有群业务查询必须包含 `group_id`。
- 主动消息保存 AstrBot 的 `unified_msg_origin`，不自行拼接平台路由键。

## 可靠性策略

- OneBot 消息使用 `(message_type, message_id)` 唯一约束，并在 Redis 使用带 TTL 的 SHA-256 去重键做快速拦截。
- PostgreSQL、Redis 均使用异步连接池；连接失败时插件降级而不拖垮 AstrBot。
- LLM 限流按用户与能力分别计数；群管理命令统一走权限服务。
- 提醒以 PostgreSQL 为真相源，通过 `FOR UPDATE SKIP LOCKED` 原子领取；重启后恢复未完成记录。
- 容器均使用 `restart: unless-stopped`、健康检查和持久化卷。
- WebUI 只绑定 `127.0.0.1`，生产访问建议通过 SSH 隧道或后续 Nginx/TLS。

## 模型路由

当前 `/think on|off` 在 `SMART_MODEL` 与 `DEFAULT_MODEL` 间显式切换；`auto` 通过确定性规则在 `FAST_MODEL`、`DEFAULT_MODEL`、`SMART_MODEL`、`CODING_MODEL` 和 `VISION_MODEL` 间路由。搜索、提醒、计算器和天气均以 Tool 接入，模型 ID 不写死在业务代码中。

## 分阶段交付

1. Phase 1（完成）：四个基础容器、数据库迁移、AstrBot 内置 AI 链路、基础设施健康插件。
2. Phase 2（完成）：消息采集、去重、权限、限流、结构化日志、业务会话索引。
3. Phase 3（完成）：搜索、提醒、群总结、统计、语录。
4. Phase 4（完成）：显式长期记忆、Vision、生图。
5. Phase 5：知识库与 Embedding 已按当前部署需求移除。
6. Phase 6（完成）：Tool Calling、可解释模型路由与工具调用可观测性。

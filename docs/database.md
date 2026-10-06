# 数据库设计

## 当前写入链路

- `messages`：守卫插件记录 QQ 入站消息与成功生成的机器人回复。
- `conversations`：记录实际发生的 LLM 用户/助手轮次，按 `unified_msg_origin` 隔离。
- `llm_usage`：记录模型、输入 Token、输出 Token、用户、群和请求 ID。
- `users`、`groups`：收到消息时自动补充基础资料。
- `lotteries`、`lottery_entries`：保存群抽奖及参与记录。
- `quotes`：保存群友语录，并按群和来源消息去重。
- `reminders`：保存待执行、处理中、已发送、已取消和失败的提醒。
- `memories`：保存用户在私聊或指定群聊范围主动创建的长期记忆。

消息正文会按照插件配置 `message_max_chars` 截断；`raw_event` 只保存平台、UMO 和时间戳等最小元数据，不保存完整 OneBot 原始事件。

完整可执行迁移位于 `deploy/postgres/init/001_schema.sql`。首次创建 PostgreSQL 数据卷时由官方镜像自动执行。

## 表

| 表 | 用途 | 关键隔离/索引 |
|---|---|---|
| `users` | QQ 用户档案 | `user_id` 唯一 |
| `groups` | 群配置 | `group_id` 唯一 |
| `messages` | 群聊原始文本 | 消息唯一约束；群/用户/时间索引 |
| `conversations` | 自定义业务对话记录 | `session_key` 唯一；群+用户+时间索引 |
| `memories` | 显式长期记忆 | 用户+群+重要性索引 |
| `reminders` | 持久提醒 | 到期扫描、用户+会话+时间部分索引 |
| `quotes` | 群友语录 | 群+用户索引；群+来源消息唯一索引 |
| `documents` | 知识库文档 | SHA-256 去重 |
| `document_chunks` | 文档块与向量 | HNSW cosine 索引 |
| `plugin_configs` | 插件作用域配置 | 插件+作用域唯一 |
| `llm_usage` | 模型用量 | 用户/全局时间索引 |
| `lotteries` | 群抽奖主记录 | 每群仅一个进行中抽奖；群+时间索引 |
| `lottery_entries` | 抽奖参与与中奖记录 | 抽奖+用户唯一 |

所有业务表含 `created_at`、`updated_at`，后者由统一触发器维护。时间统一用 `TIMESTAMPTZ`。QQ ID 使用 `TEXT`，避免平台 ID 范围或前导字符假设。

## 预留向量表

初始迁移中仍保留 `documents`、`document_chunks` 和 pgvector 结构，避免删除已存在的数据；当前运行配置没有挂载知识库插件，也不需要配置 Embedding 模型。

## 迁移约定

- 已运行环境不得修改旧迁移；新增 `002_*.sql`、`003_*.sql`。
- `/docker-entrypoint-initdb.d` 只在空数据卷初始化时执行，不是持续迁移器。
- 当前使用 `001_schema.sql` 到 `005_memory.sql`；现有数据卷需按 README 手动应用新增迁移。
- 删除数据、改变向量维度或大表重建索引前必须先备份并演练恢复。

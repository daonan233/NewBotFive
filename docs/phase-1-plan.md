# Phase 1 开发计划与验收

## 交付范围

- [x] NapCatQQ、AstrBot、PostgreSQL/pgvector、Redis 的 Compose 拓扑。
- [x] 持久化卷、内部数据库网络、健康检查、重启策略。
- [x] 完整初始 SQL Schema。
- [x] AstrBot Star 基础插件和异步连接池。
- [x] `.env.example` 与从空 Linux 服务器开始的部署文档。
- [ ] 在真实服务器扫码登录 QQ（需要用户现场操作）。
- [ ] 在 WebUI 配置真实 LLM Provider 和 OneBot 适配器（需要真实密钥与账号）。
- [ ] 完成真实 QQ → AstrBot → LLM → QQ 冒烟测试。

## 实施顺序

1. 复制 `.env.example`，填写强密码、NapCat Token 和模型密钥。
2. `docker compose config` 校验配置。
3. 启动数据库与 Redis，确认健康。
4. 启动 AstrBot，登录 WebUI，配置 OpenAI Compatible Provider。
5. 启用 `builtin_commands_extension`，配置管理员与会话隔离。
6. 启动 NapCat，扫码登录，在其 WebUI 新建反向 WebSocket 客户端。
7. 在私聊与群聊分别测试消息、上下文、重置、模型和健康命令。
8. 备份卷并验证恢复步骤后，才能进入 Phase 2。

## 验收命令

```bash
docker compose config --quiet
docker compose up -d postgres redis
docker compose ps
docker compose exec postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"
docker compose exec redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning ping
docker compose up -d astrbot napcat
docker compose logs --tail=200 astrbot napcat
```

QQ 侧验收：

- 私聊发送“你好”，应获得模型回复。
- 群聊 `@机器人 你好`，应获得模型回复；未 @ 的普通聊天不应触发（按 WebUI 唤醒策略配置）。
- 连续追问可利用上下文；另一用户和另一群不能读到当前上下文。
- `/reset` 清空当前对话；`/help` 可用；管理员 `/model` 可用。
- 管理员 `/qqai_status` 返回 PostgreSQL 与 Redis 正常。

## 进入 Phase 2 的门槛

Compose 校验通过、四容器稳定运行、OneBot 日志显示适配器已连接、真实模型返回成功、隔离测试通过、备份文件可恢复。任一项失败时先修 Phase 1，不叠加新功能。


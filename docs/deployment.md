# 部署与运维说明

详细首装步骤见根目录 `README.md`。这里记录生产约定。

## 网络

- `bot_backend` 是 internal 网络，仅 PostgreSQL、Redis、AstrBot 可见。
- NapCat 与 AstrBot 通过 `bot_frontend` 通信。
- AstrBot WebUI `6185` 与 NapCat WebUI `6099` 只监听宿主机回环地址。
- OneBot 反向 WebSocket 使用容器地址 `ws://astrbot:6199/ws`，不需要向公网发布 6199。

## 持久化

`postgres_data`、`redis_data`、`astrbot_data`、`napcat_config`、`napcat_qq` 均为命名卷。执行 `docker compose down` 不会删除；不要使用 `down -v`，除非明确要销毁全部数据。

## 备份

优先做逻辑备份：

```bash
mkdir -p backups
docker compose exec -T postgres pg_dump \
  -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc \
  > "backups/postgres-$(date +%F-%H%M%S).dump"
docker compose run --rm --no-deps \
  -v "$(pwd)/backups:/backup" \
  astrbot sh -c 'tar -C /AstrBot/data -czf /backup/astrbot-data.tgz .'
```

恢复前先停写并在测试环境演练。PostgreSQL 自定义格式用 `pg_restore --clean --if-exists` 恢复。

## 更新

先备份，再修改 `.env` 中的精确镜像标签，执行：

```bash
docker compose pull
docker compose up -d
docker compose ps
docker compose logs --tail=200 astrbot napcat postgres redis
```

不要直接在生产环境追随 beta 标签。插件源代码以只读挂载进入 AstrBot，修改后从 WebUI 重载插件或重启 AstrBot。


# QQ AI 超级机器人

一个可在 Windows 或 Linux 上部署的 QQ AI 机器人项目。项目使用 AstrBot 负责 AI 对话与插件系统，NapCatQQ 负责接入 QQ，PostgreSQL + pgvector 保存业务数据，Redis 保存缓存和会话状态。

> 请遵守 QQ 平台规则，建议先使用测试 QQ、小群和低频场景验证。不要在配置文件、截图或聊天记录中公开 QQ 密码、API Key 等敏感信息。

## 已实现功能

- QQ 私聊与群聊 AI 对话
- 群内 `@机器人`、私聊、指令触发
- 多模型配置与切换
- 按用户、按会话切换普通/推理模型
- 群抽奖：创建、报名、查询、开奖、取消
- 掷骰子和随机选择小游戏
- PostgreSQL 持久化抽奖数据，Redis 保存思考模式状态
- 所有群聊/私聊消息异步写入 PostgreSQL，群消息可供后续总结与统计
- Redis 原子去重，避免 OneBot 重连时重复处理同一条消息
- 按用户限制 AI 调用频率，超级管理员自动放行
- 记录模型、请求次数和 Token 用量
- 统一识别普通用户、群管理员和机器人超级管理员
- 群聊总结、今日/本周/本月统计与群友语录
- PostgreSQL 持久化提醒，支持重启恢复、列表和取消
- Tavily/Serper 可插拔联网搜索与模型 Tool Calling
- 显式长期记忆，可按私聊/群聊范围查看和删除，并自动注入后续对话
- QQ 图片理解与 Vision 模型路由
- OpenAI Compatible Images API 生图与 Redis 限流
- 从只读挂载的本地图库随机发送图片
- 可解释的 Fast/Default/Smart/Coding/Vision 规则路由
- 安全数学计算器与 Open-Meteo 实时天气 Agent Tools
- AstrBot WebUI 和 NapCat WebUI
- 基础健康检查、日志、备份与故障排查命令

## 架构

```text
QQ 用户 / QQ 群
      │
      ▼
  NapCatQQ
      │  OneBot v11 WebSocket
      ▼
   AstrBot ─────────► AI 模型 API
      │
      ├─────────────► PostgreSQL + pgvector
      └─────────────► Redis
```

默认端口：

| 服务 | 地址 | 用途 |
|---|---|---|
| AstrBot WebUI | `http://127.0.0.1:6185` | 模型、平台和插件配置 |
| NapCat WebUI | `http://127.0.0.1:6099` | QQ 登录和 OneBot 配置 |
| AstrBot OneBot WS | 容器内 `ws://astrbot:6199/ws` | NapCat 连接 AstrBot |

## 目录说明

```text
.
├─ docker-compose.yml
├─ .env.example
├─ config/
│  └─ config.example.yaml
├─ assets/
│  └─ random_images/
├─ deploy/
│  └─ postgres/init/
├─ docs/
├─ plugins/
│  ├─ astrbot_plugin_qq_ai_core/
│  ├─ astrbot_plugin_qq_ai_fun/
│  ├─ astrbot_plugin_qq_ai_guard/
│  ├─ astrbot_plugin_qq_ai_group/
│  ├─ astrbot_plugin_qq_ai_reminder/
│  ├─ astrbot_plugin_qq_ai_search/
│  ├─ astrbot_plugin_qq_ai_memory/
│  ├─ astrbot_plugin_qq_ai_media/
│  └─ astrbot_plugin_qq_ai_tools/
├─ scripts/
├─ src/qq_ai_bot/
└─ tests/
```

## Windows 快速启动

### 1. 准备环境

安装并启动 Docker Desktop，容器运行方式选择 **WSL2**，并确认 Docker Desktop 已完全启动。

在 PowerShell 中执行：

```powershell
Set-Location D:\BotFive_new
docker version
docker compose version
```

如果 `docker version` 提示无法连接 `dockerDesktopLinuxEngine`，说明 Docker Desktop 尚未启动，或 WSL2 引擎还未就绪。

### 2. 创建配置文件

首次部署时执行：

```powershell
Copy-Item .env.example .env
notepad .env
```

至少修改以下配置：

```dotenv
POSTGRES_PASSWORD=请替换为强密码
REDIS_PASSWORD=请替换为强密码
OPENAI_API_KEY=你的模型API密钥
OPENAI_BASE_URL=https://你的模型服务地址/v1
DEFAULT_MODEL=普通模型ID
SMART_MODEL=推理模型ID
```

说明：

- `DEFAULT_MODEL`：`/think off` 和 `/think auto` 使用的普通模型。
- `SMART_MODEL`：`/think on` 使用的推理模型；没有推理模型时可暂时留空。
- 两个模型 ID 都必须能被当前 AstrBot 模型供应商调用。
- `.env` 不应提交到 Git，也不要把真实密钥发到群里。
- QQ 不需要在 `.env` 中填写密码，后面通过 NapCat WebUI 扫码登录。

### 3. 启动全部服务

```powershell
docker compose --env-file .env up -d
docker compose ps
```

正常情况下应看到：

- `postgres`：`Up (healthy)`
- `redis`：`Up (healthy)`
- `astrbot`：`Up`
- `napcat`：`Up`

查看实时日志：

```powershell
docker compose logs -f --tail=100 astrbot napcat
```

按 `Ctrl+C` 只会退出日志查看，不会停止机器人。

## Linux 快速启动

```bash
cp .env.example .env
nano .env
docker compose --env-file .env up -d
docker compose ps
```

如果只想先启动数据服务：

```bash
docker compose --env-file .env up -d postgres redis
```

## 首次配置

### 1. 配置 AstrBot 模型

打开 `http://127.0.0.1:6185`，进入模型供应商配置：

1. 新建一个 OpenAI 兼容供应商。
2. 填写 API Key、API Base URL 和模型 ID。
3. API Base URL 通常应以 `/v1` 结尾。
4. 保存后使用 WebUI 的模型列表或测试功能验证。
5. 将普通模型设置为默认模型。

如果需要 `/think on`：

- 在 `.env` 中填写 `SMART_MODEL` 后重建 AstrBot；或
- 在 AstrBot 插件管理中打开 `qq_ai_fun` 配置，填写 `reasoning_model`。

修改 `.env` 后执行：

```powershell
docker compose --env-file .env up -d --force-recreate astrbot
```

### 2. 配置 AstrBot 的 OneBot 平台

在 AstrBot WebUI 中新增 OneBot v11 平台适配器，并启动该适配器。项目默认监听：

```text
0.0.0.0:6199
```

### 3. 登录 NapCatQQ

打开 `http://127.0.0.1:6099`：

1. 用准备好的 QQ 扫码登录。
2. 建议首次登录后在手机 QQ 中确认设备。
3. 在 NapCat 中新增 OneBot 11 **WebSocket Client**。
4. WebSocket 地址填写：

```text
ws://astrbot:6199/ws
```

5. 启用连接并保存。

这里必须使用 Docker 服务名 `astrbot`，不要填写 `127.0.0.1` 或 `localhost`，因为 NapCat 和 AstrBot 运行在不同容器中。

### 4. 验证连接

```powershell
docker compose logs --tail=100 astrbot napcat
```

AstrBot 日志中出现 OneBot 连接成功后，即可在 QQ 中发送：

```text
/help
/qqai_status
```

## 指令说明

### 基础指令

| 指令 | 说明 |
|---|---|
| `/help` | 查看 AstrBot 帮助 |
| `/provider` | 查看或切换模型供应商 |
| `/model` | 查看或切换模型 |
| `/persona` | 管理员查看或切换当前 QQ 会话的人格 |
| `/new` | 新建对话 |
| `/reset` | 重置当前对话 |
| `/qqai_status` | 查看 QQ AI 核心插件状态 |
| `/usage` | 查看本人今日 AI 请求与 Token 用量 |
| `/usage today` | 管理员查看今日全局 AI 用量 |
| `/qqai_guard_status` | 管理员查看限流、去重和消息落库状态 |
| `/summary [条数]` | 总结当前群最近的聊天内容 |
| `/stats [today\|week\|month]` | 查看群活跃统计 |
| `/quote` | 随机查看本群语录 |

### 思考模式

| 指令 | 说明 |
|---|---|
| `/think` | 查看当前模式 |
| `/think on` | 使用推理模型 |
| `/think off` | 使用普通模型 |
| `/think auto` | 恢复 Fast/Default/Smart/Coding 规则路由 |

思考模式按“用户 + 当前会话”保存，因此同一用户可以在不同群聊或私聊中使用不同模式。`on/off` 是显式覆盖；`auto` 会按短问题、复杂分析、代码和图片选择已配置模型，缺失的专用模型回退到 `DEFAULT_MODEL`。该功能不会显示或泄露模型的内部思维链。

如果执行 `/think on` 后提示未配置推理模型，请填写 `SMART_MODEL` 或插件配置中的 `reasoning_model`。

### 群抽奖

| 指令 | 说明 |
|---|---|
| `/lottery help` | 查看抽奖帮助 |
| `/lottery start 2 奶茶券` | 创建 2 个中奖名额的“奶茶券”抽奖 |
| `/lottery join` | 参加当前群抽奖 |
| `/lottery status` | 查看奖品、人数和状态 |
| `/lottery draw` | 随机开奖 |
| `/lottery cancel` | 取消当前抽奖 |

规则：

- 仅支持群聊，每个群同一时间只能有一个进行中的抽奖。
- 同一 QQ 只能报名一次。
- 中奖者通过数据库随机排序抽取，不会重复中奖。
- 如果报名人数少于中奖名额，则所有参与者中奖。
- 默认允许群成员发起抽奖，可在插件配置中启用 `lottery_admin_only_start`，限制为管理员发起。
- 开奖和取消仅允许创建者或管理员操作。
- 抽奖记录保存在 PostgreSQL，重启容器不会丢失。

### 小游戏

| 指令 | 示例 | 说明 |
|---|---|---|
| `/roll [面数]` | `/roll 20` | 掷一个 2～1000 面的骰子，默认 6 面 |
| `/pick 选项1\|选项2\|选项3` | `/pick 火锅\|烧烤\|炒菜` | 从 2～20 个选项中随机选择一个 |

### 群聊助手

| 指令 | 说明 |
|---|---|
| `/summary` | 总结最近 100 条群消息 |
| `/summary 200` | 总结最近 200 条群消息，最大值可配置 |
| `/stats today` | 今日消息量、活跃人数、时段、关键词和活跃用户 |
| `/stats week` | 本周群聊统计 |
| `/stats month` | 本月群聊统计 |
| 回复消息后 `/quote add` | 收录一条群友语录 |
| `/quote` | 随机展示本群语录 |

### 持久化提醒

| 指令 | 示例 |
|---|---|
| `/remind 时间 内容` | `/remind 10分钟后 喝水` |
| `/remind 时间 内容` | `/remind 明天 09:00 签到` |
| `/remind 时间 内容` | `/remind 2026-10-10 15:00 开会` |
| `/remind list` | 查看当前会话最多 20 条待执行提醒 |
| `/remind cancel 编号` | 取消自己在当前会话中的提醒 |

提醒保存在 PostgreSQL。机器人重启时会恢复未完成任务；发送失败会自动重试，群聊到期时会 `@` 创建者。模型也可以通过 `create_reminder` Tool 创建提醒。

### 联网搜索

在 `.env` 中配置一种搜索供应商：

```dotenv
SEARCH_PROVIDER=tavily
SEARCH_API_KEY=你的搜索服务密钥
# 使用官方地址时留空；自建兼容服务才填写
SEARCH_API_BASE=
```

也可以将 `SEARCH_PROVIDER` 改为 `serper`。修改后执行：

```powershell
docker compose --env-file .env up -d --force-recreate astrbot
```

使用 `/search 要搜索的问题` 获取带链接的结果。模型需要最新信息时可调用 `web_search` Tool；普通用户默认每分钟最多搜索 5 次。

### 长期记忆

| 指令 | 说明 |
|---|---|
| `/remember 我喜欢 BanG Dream` | 在当前私聊或群聊范围保存记忆 |
| `/memory` | 查看自己在当前范围保存的记忆 |
| `/forget 12` | 删除编号为 12 且属于自己的当前范围记忆 |

长期记忆会作为低优先级背景资料注入后续模型请求，不会把记忆中的命令式文本当作系统指令。群内记忆不会泄漏到其他群。

### 图片理解与 AI 生图

发送图片并附带 `/vision 这是什么？` 可显式调用图片理解。普通的图片对话也会在存在图片输入时优先路由到 `VISION_MODEL`；未配置时仍使用 AstrBot 当前模型。

生图需要在 `.env` 配置：

```dotenv
IMAGE_API_BASE=https://你的兼容服务地址/v1
IMAGE_API_KEY=你的图片服务密钥
IMAGE_MODEL=你的生图模型ID
IMAGE_RATE_LIMIT_PER_MINUTE=2
```

配置后使用 `/draw 一只戴墨镜的柴犬`。服务兼容返回图片 URL 或 `b64_json`；Base64 图片保存在 AstrBot 持久卷中。

### 本地随机图片

在 `.env` 中填写宿主机图片目录。Windows 路径建议使用正斜杠：

```dotenv
RANDOM_IMAGE_HOST_DIR=H:/个人/pixiv/r18
```

项目使用同步脚本把图片导入 Docker 内部图库卷，AstrBot 和 NapCat 都以只读方式使用该卷。这样即使图片位于 U 盘或移动硬盘，也不依赖 Docker Desktop 直接挂载可移动磁盘。

```powershell
.\scripts\sync-random-images.ps1
```

也可以临时指定其他来源目录：

```powershell
.\scripts\sync-random-images.ps1 -SourceDir 'H:\个人\pixiv\r18'
```

首次导入或本地目录新增、替换图片后重新运行同步脚本。同步采用合并/覆盖方式，不会删除 Docker 图库卷中已经存在但源目录后来删除的旧文件。

使用方式：

| 指令 | 说明 |
|---|---|
| `/randompic` | 从配置的目录或其子目录随机发送一张图片 |
| `/随机图片` | 中文别名 |
| `/来张图` | 中文别名 |

支持 `.jpg`、`.jpeg`、`.png`、`.gif`、`.webp` 和 `.bmp`。插件默认递归扫描子目录，所有群成员和私聊用户都可以使用。可在 AstrBot WebUI 的 `qq_ai_media` 插件配置中修改：

| 配置项 | 作用 |
|---|---|
| `local_random_enabled` | 是否启用本地随机图片 |
| `local_random_dir` | 容器内图库路径，通常无需修改 |
| `local_random_recursive` | 是否扫描子文件夹 |

不要在 WebUI 中填写 `H:\个人\pixiv\r18`；WebUI 使用容器内路径，Windows 宿主机路径只填写在 `.env` 的 `RANDOM_IMAGE_HOST_DIR`。图库卷内路径固定为 `/AstrBot/data/qq_ai_random_images`。

### 通用 Agent 工具

| 指令 | 说明 |
|---|---|
| `/calc sqrt(81) + 2 ** 3` | 使用 AST 白名单安全计算，不执行 Python 代码 |
| `/weather 北京` | 查询实时天气与三日预报 |

模型可调用 `calculator` 和 `get_weather` Tool。天气使用 Open-Meteo，无需 API Key；工具调用日志只记录工具名、用户和群，不记录完整参数或返回内容。

## 插件配置

在 AstrBot WebUI 的插件管理中找到 `qq_ai_fun`，可配置：

| 配置项 | 作用 |
|---|---|
| `normal_model` | 普通模式模型 ID；留空时使用 `DEFAULT_MODEL` |
| `reasoning_model` | 推理模式模型 ID；留空时使用 `SMART_MODEL` |
| `fast_model` | 短问题模型 ID；留空时使用 `FAST_MODEL` |
| `coding_model` | 代码问题模型 ID；留空时使用 `CODING_MODEL` |
| `lottery_admin_only_start` | 是否只允许管理员创建抽奖 |
| `lottery_max_winners` | 单次抽奖最大中奖人数 |

插件配置优先级高于 `.env`。

在插件管理中找到 `qq_ai_guard`，可配置：

| 配置项 | 作用 |
|---|---|
| `store_messages` | 是否保存收到的群聊和私聊消息 |
| `deduplicate_messages` | 是否使用 Redis 拦截重复消息 |
| `dedup_ttl_seconds` | 消息去重标记保留时间 |
| `ai_rate_limit_per_minute` | 普通用户每分钟 AI 请求上限 |
| `message_max_chars` | 单条消息最大入库长度 |
| `timezone` | `/usage` 今日统计使用的时区 |

机器人超级管理员通过 `.env` 的 `SUPER_USERS` 配置，多个 QQ 号使用英文逗号分隔。

`qq_ai_group` 可配置总结默认条数、最大条数、语录是否仅管理员可收录和统计时区；`qq_ai_reminder` 可配置扫描间隔、时区和失败重试次数；`qq_ai_search` 可选择 Tavily/Serper、结果数和超时；`qq_ai_memory` 可配置容量和注入数量；`qq_ai_media` 可配置 Vision/生图模型与超时。

## 人格配置与同步到 QQ

项目提供了可直接使用的丸山彩人格文件：`prompts/maruyama_aya.md`。在 AstrBot WebUI 修改人格后，不需要再复制到 NapCat；QQ 消息本来就由 NapCat 转发给当前 AstrBot 实例处理。

### 让所有 QQ 会话默认使用该人格

1. 打开 AstrBot WebUI：`http://127.0.0.1:6185`。
2. 进入人格管理，创建或编辑人格并保存。使用丸山彩人设时，可将 `prompts/maruyama_aya.md` 的正文粘贴到系统提示词。
3. 进入“配置”，选中当前 QQ 平台实际使用的配置文件。
4. 在该配置文件的“AI”区域，将默认人格选择为刚保存的人格。
5. 点击页面右下角“保存”。
6. 回到 QQ 对目标私聊或群聊发送 `/new`，然后重新 `@机器人` 测试，例如“你是谁？”。

WebUI 保存后通常会直接对新的模型请求生效，不需要修改 NapCat，也不需要重启整个项目。`/new` 会开启一段不带旧上下文的新对话，适合确认新人格是否已经生效；`/reset` 可用于清空当前对话上下文。

### 只让某个群或私聊使用该人格

1. 在目标 QQ 群或私聊中发送 `/sid`，取得当前会话的 UMO/会话标识。
2. 在 AstrBot WebUI 打开“更多功能”→“自定义规则”。
3. 新建规则，选择该会话标识，并把人格绑定为目标人格后保存。
4. 回到同一个 QQ 会话发送 `/new`，再测试机器人回复。

自定义规则的优先级高于配置文件中的默认人格，所以它适合为某一个群设置专属角色。如果全局人格已经更改但某个群仍使用旧人格，应先检查这里是否存在覆盖规则。

管理员也可以直接在目标 QQ 会话发送 `/persona`，按照机器人返回的菜单查看或切换当前会话人格。该指令由 AstrBot 的 `builtin_commands_extension` 提供，需要保持该内置扩展启用，并且发送者必须已配置为 AstrBot 管理员。

人格只影响模型的说话方式，不会改变插件权限、限流和安全规则。

## 数据库升级

全新部署时，PostgreSQL 会自动执行 `deploy/postgres/init/` 中的初始化脚本。

如果是在已经存在的数据库卷上升级，可依次执行尚未应用的迁移：

```powershell
docker compose exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/002_fun.sql'
docker compose exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/003_group.sql'
docker compose exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/004_reminder.sql'
docker compose exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/005_memory.sql'
```

然后重建 AstrBot：

```powershell
docker compose --env-file .env up -d --force-recreate astrbot
```

## 日常维护

启动：

```powershell
docker compose --env-file .env up -d
```

停止：

```powershell
docker compose down
```

查看状态：

```powershell
docker compose ps
```

查看日志：

```powershell
docker compose logs -f --tail=200 astrbot napcat
```

重启机器人服务：

```powershell
docker compose restart astrbot napcat
```

更新镜像并重建：

```powershell
docker compose pull
docker compose --env-file .env up -d
```

运行测试：

```powershell
python -m unittest discover -s tests -v
```

## 备份

创建备份目录并导出 PostgreSQL：

```powershell
New-Item -ItemType Directory -Force backups | Out-Null
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists' > backups\postgres.sql
```

备份 Docker 卷中的 AstrBot 与 NapCat 配置/QQ 数据：

```powershell
docker run --rm -v qq-ai-bot_astrbot_data:/data -v ${PWD}\backups:/backup alpine tar czf /backup/astrbot_data.tar.gz -C /data .
docker run --rm -v qq-ai-bot_random_image_data:/data -v ${PWD}\backups:/backup alpine tar czf /backup/random_image_data.tar.gz -C /data .
docker run --rm -v qq-ai-bot_napcat_config:/data -v ${PWD}\backups:/backup alpine tar czf /backup/napcat_config.tar.gz -C /data .
docker run --rm -v qq-ai-bot_napcat_qq:/data -v ${PWD}\backups:/backup alpine tar czf /backup/napcat_qq.tar.gz -C /data .
```

实际卷名可先用 `docker volume ls` 查看；如果项目目录名不同，Compose 生成的卷名前缀也会不同。

## 常见问题

### Docker 提示无法连接 `dockerDesktopLinuxEngine`

启动 Docker Desktop，确认容器模式为 WSL2，并等待左下角显示 Engine running。然后重新执行：

```powershell
docker version
docker compose ps
```

### PostgreSQL 或 Redis 一直不是 healthy

```powershell
docker compose logs --tail=200 postgres redis
```

重点检查 `.env` 中的密码是否为空、格式是否包含未转义特殊字符，以及磁盘空间是否充足。

### NapCat 提示 `ECONNREFUSED`

先确认 AstrBot WebUI 中已经创建并启用 OneBot v11 平台，再检查 NapCat 地址是否为：

```text
ws://astrbot:6199/ws
```

随后重启连接：

```powershell
docker compose restart astrbot napcat
```

### 模型列表返回 HTML 或 404

通常是 API Base URL 填到了服务首页。OpenAI 兼容接口一般应使用：

```text
https://你的模型服务地址/v1
```

同时确认 API Key 和模型 ID 与供应商控制台一致。

### `/think on` 无法启用

确认已经设置 `SMART_MODEL` 或插件配置 `reasoning_model`，并确保该模型 ID 能由当前 AstrBot 模型供应商调用。修改后重建 AstrBot 或在 WebUI 中重载插件。

### WebUI 已修改人格，但 QQ 回复没有变化

依次检查：

1. 人格内容和当前配置文件都已经点击“保存”。
2. QQ 的 OneBot 平台使用的正是被修改的配置文件。
3. “更多功能”→“自定义规则”中没有给当前会话绑定其他人格。
4. 在目标 QQ 会话发送 `/new`，避免旧对话上下文继续影响回复。
5. 管理员发送 `/persona`，确认当前会话实际选中的人格。

仍未生效时查看 AstrBot 日志；最后再尝试只重启 AstrBot：

```powershell
docker compose logs --tail=100 astrbot
docker compose --env-file .env restart astrbot
```

### `/randompic` 提示目录中没有图片

先确认 `.env` 中的 `RANDOM_IMAGE_HOST_DIR` 指向真实目录，然后重新同步：

```powershell
.\scripts\sync-random-images.ps1
```

可用下面的命令检查 AstrBot 容器是否已经能看到图片：

```powershell
docker compose exec -T astrbot python -c "from pathlib import Path; p=Path('/AstrBot/data/qq_ai_random_images'); print(sum(1 for x in p.rglob('*') if x.is_file()))"
```

输出大于 `0` 后，`/randompic` 才能正常发送。AstrBot 和 NapCat 对图库卷均为只读；同步脚本通过一次性辅助容器写入图库，不会修改或删除 H 盘原文件。

### 指令没有反应

依次检查：

1. AstrBot 日志中是否显示 OneBot 已连接。
2. 群里是否需要 `@机器人`。
3. 日志中目标 `qq_ai_*` 插件是否显示“初始化完成”。
4. 是否触发了 QQ 风控或频率限制。

```powershell
docker compose logs --tail=300 astrbot napcat
```

## 安全建议

- 立即更换任何曾经公开过的 QQ 密码和 API Key。
- 给 QQ 开启设备锁和登录保护，优先使用专门的机器人账号。
- 不要把 PostgreSQL、Redis、OneBot WebSocket 暴露到公网。
- WebUI 如需公网访问，应放在 HTTPS 反向代理和额外身份验证后面。
- 为模型设置请求频率、每日额度和管理员白名单。
- 定期备份数据库和 Docker 卷。

## 更多文档

- `docs/architecture.md`：系统架构
- `docs/directory-structure.md`：目录结构
- `docs/deployment.md`：部署流程
- `docs/database.md`：数据库说明
- `docs/plugins.md`：插件开发说明
- `docs/phase-1-plan.md`：第一阶段实施计划
- `docs/research.md`：技术调研记录

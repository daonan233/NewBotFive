# 插件设计

## 当前插件

- `astrbot_plugin_qq_ai_core`：PostgreSQL、Redis 基础设施健康检查。
- `astrbot_plugin_qq_ai_fun`：思考模型路由、群抽奖、骰子和随机选择。
- `astrbot_plugin_qq_ai_guard`：消息落库、OneBot 消息去重、AI 限流、权限与 Token 用量统计。
- `astrbot_plugin_qq_ai_group`：群聊总结、活跃统计和群友语录。
- `astrbot_plugin_qq_ai_reminder`：持久化提醒、失败重试、启动恢复及 `create_reminder` Tool。
- `astrbot_plugin_qq_ai_search`：Tavily/Serper 搜索、Redis 限流及 `web_search` Tool。
- `astrbot_plugin_qq_ai_memory`：显式长期记忆及安全的模型上下文注入。
- `astrbot_plugin_qq_ai_media`：QQ 图片理解、Vision 路由和兼容 Images API 生图。
- `astrbot_plugin_qq_ai_tools`：安全计算器和 Open-Meteo 天气查询。

共享权限逻辑位于 `common/qq_ai_common/permissions.py`，通过只读 Volume 挂载到 AstrBot，避免各插件重复解析 `SUPER_USERS`。

## 实现约定

`astrbot_plugin_qq_ai_core` 遵循当前 AstrBot Star 规范：入口必须是 `main.py`，元数据放在 `metadata.yaml`，可视化配置放在 `_conf_schema.json`。入口只注册事件和命令，连接池与业务代码拆到独立模块。

`astrbot_plugin_qq_ai_fun` 提供按用户/会话保存的思考模式路由和群抽奖小游戏。思考开关通过当前公开的 `ProviderRequest.model` 在普通模型与推理模型之间路由，不修改 Provider 私有请求参数。

管理员命令：

- `/qqai_status`：检查 PostgreSQL 和 Redis。
- `/think on|off|auto`：开启、关闭或恢复默认思考模型路由。
- `/lottery help`：查看抽奖命令；支持创建、参加、状态、开奖和取消。
- `/roll [面数]`：骰子；`/pick A|B|C`：随机选择。

聊天、`/help`、`/reset`、`/new` 使用 AstrBot 主程序能力，`/model` 由官方 `builtin_commands_extension` 插件提供。`/stats` 由群助手实现；清空上下文使用官方 `/reset`。

## 插件边界

```text
plugins/
├── astrbot_plugin_qq_ai_core/       # 连接、健康、共享约定
├── astrbot_plugin_qq_ai_guard/      # 消息落库、去重、限流（已实现）
├── astrbot_plugin_qq_ai_search/     # Search Tool（已实现）
├── astrbot_plugin_qq_ai_reminder/   # 提醒与恢复扫描（已实现）
├── astrbot_plugin_qq_ai_group/      # 总结、统计、语录（已实现）
├── astrbot_plugin_qq_ai_memory/     # 显式长期记忆（已实现）
├── astrbot_plugin_qq_ai_media/      # Vision 与生图（已实现）
├── astrbot_plugin_qq_ai_tools/      # Calculator / Weather Tools（已实现）
└── astrbot_plugin_qq_ai_manager/    # 欢迎、关键词、群管理
```

每个插件必须具备自己的 `metadata.yaml`、`main.py`、配置 Schema、服务模块和测试，并能由 AstrBot 独立禁用。插件间不直接访问彼此的私有实现；共享能力稳定后再抽成独立 Python 包，避免早期过度设计。

## 编码规则

- Handler 只解析输入与生成回复；查询、网络与业务规则放 service/repository。
- 网络 I/O 全部异步，并设置超时。
- 不记录密码、API Key、完整原始事件或不必要的隐私信息。
- 平台路由使用 `event.unified_msg_origin`，不用仅含会话号的 `session_id`。
- 管理命令使用官方 `PermissionType.ADMIN`；业务超级管理员再由统一权限服务补充。
- Tool 使用 AstrBot 当前 `@filter.llm_tool` 声明，并在 docstring 的 `Args` 中提供参数类型。

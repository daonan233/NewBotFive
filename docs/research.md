# 官方规范核对记录（2026-10-06）

本设计只采用官方文档或官方仓库中的当前说明：

- [AstrBot 插件开发指南](https://docs.astrbot.app/dev/star/plugin-new.html)：插件目录、`metadata.yaml`、依赖与异步网络约定。
- [AstrBot 最小插件实例](https://docs.astrbot.app/dev/star/guides/simple.html)：`Star`、`Context`、`main.py` 和命令 Handler。
- [AstrBot 插件配置](https://docs.astrbot.app/dev/star/guides/plugin-config.html)：`_conf_schema.json` 与 `AstrBotConfig` 注入。
- [AstrBot AI/Tool 接口](https://docs.astrbot.app/dev/star/guides/ai.html)：当前 LLM 调用和 `add_llm_tools`。
- [AstrBot OneBot v11 接入](https://docs.astrbot.app/platform/aiocqhttp.html)：AstrBot 作为反向 WebSocket 服务端，URL 为 `/ws`。
- [AstrBot 内置指令](https://docs.astrbot.app/use/command.html)：`/help`、`/reset`、`/new`、`/stats` 与扩展插件提供的 `/model`。
- [AstrBot 模型服务](https://docs.astrbot.app/en/providers/llm.html)：OpenAI Compatible Provider 与环境变量密钥引用。
- [AstrBot 官方 Compose](https://github.com/AstrBotDevs/AstrBot/blob/master/compose.yml)：端口、数据目录和镜像。
- [NapCat-Docker 的 AstrBot Compose](https://github.com/NapNeko/NapCat-Docker/blob/main/compose/astrbot.yml)：`MODE=astrbot`、挂载和容器网络。
- [NapCat OneBot 网络基础](https://napneko.github.io/onebot/network)：WebSocket 客户端/服务端角色。

稳定版基线为 AstrBot 4.28 系列；4.29.0-beta.1 是预发布版，不作为生产基线。Compose 默认保留官方 `latest` 镜像名以确保可拉取，生产部署应在验证后将 `.env` 的镜像值固定为已测试标签或 digest。


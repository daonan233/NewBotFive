# 目录结构

```text
qq-ai-bot/
├── docker-compose.yml                  # 四个服务与持久化卷
├── .env.example                       # 无真实密钥的配置模板
├── README.md                          # Windows / Linux 部署与使用说明
├── deploy/
│   └── postgres/
│       └── init/
│           └── 001_schema.sql         # pgvector 扩展和完整初始表结构
├── docs/
│   ├── architecture.md
│   ├── database.md
│   ├── deployment.md
│   ├── directory-structure.md
│   ├── phase-1-plan.md
│   ├── plugins.md
│   └── research.md
├── plugins/
│   ├── astrbot_plugin_qq_ai_core/
│   │   ├── main.py                    # AstrBot Star 入口
│   │   ├── service.py                 # 生命周期和健康检查
│   │   ├── database.py                # asyncpg 连接池
│   │   ├── cache.py                   # redis.asyncio 连接池
│   │   ├── config.py                  # 环境变量解析
│   │   ├── _conf_schema.json          # AstrBot 可视化插件配置
│   │   ├── metadata.yaml              # AstrBot 必需元数据
│   │   └── requirements.txt           # 插件第三方依赖
│   ├── astrbot_plugin_qq_ai_fun/      # 思考模式、抽奖、骰子与随机选择
│   ├── astrbot_plugin_qq_ai_guard/    # 落库、去重、限流与用量
│   ├── astrbot_plugin_qq_ai_group/    # 总结、统计与语录
│   ├── astrbot_plugin_qq_ai_reminder/ # 持久化提醒
│   └── astrbot_plugin_qq_ai_search/   # 联网搜索与 LLM Tool
└── tests/
    ├── test_settings.py               # 基础配置单元测试
    ├── test_fun_commands.py           # 抽奖与小游戏解析测试
    ├── test_reminder_parser.py        # 提醒时间解析测试
    └── test_search_providers.py       # 搜索响应解析测试
```

当前目录已包含 Phase 1～3 的基础设施、稳定性与群工具插件；后续能力边界见 `plugins.md`。

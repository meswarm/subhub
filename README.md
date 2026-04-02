![许可证](https://img.shields.io/github/license/meswarm/subhub?label=许可证)

[![语言-中文](https://img.shields.io/badge/语言-中文-green)](README.md)
[![Language-English](https://img.shields.io/badge/Language-English-blue)](README_EN.md)

# SubHub

> 基于 LLM Function Calling 的终端交互式个人订阅管理系统

SubHub 通过自然语言对话管理你的所有订阅服务。内置大模型驱动的智能助手，支持订阅的增删改查、自动推算扣款日期、提前 3 天扣款提醒，以及月度费用统计报表。无论是月付、年付还是永久买断，SubHub 统一管理。

## 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.12+ |
| LLM | qwen3.5-flash（OpenAI 兼容 API） |
| 包管理 | uv + hatchling |
| 数据存储 | JSON 文件 |
| 测试 | pytest |

## 快速开始

### 前置要求

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) 包管理器

### 安装

```bash
git clone https://github.com/meswarm/subhub.git
cd subhub
uv pip install -e .
```

### 配置

```bash
cp .env.example .env
# 编辑 .env 填入你的 DashScope API Key
```

`config.toml` 中可自定义数据路径、提醒参数、报表货币等配置。

### 本地运行

```bash
uv run subhub
```

## 项目结构

```
subhub/
├── config.toml             # 应用配置
├── .env.example            # 环境变量模板
├── pyproject.toml          # 项目元数据与依赖
├── src/subhub/
│   ├── config.py           # 配置加载
│   ├── store.py            # JSON 数据存储层
│   ├── display.py          # Markdown 格式化输出
│   ├── tools.py            # LLM Function Calling 工具
│   ├── reminder.py         # 后台提醒线程
│   ├── chat.py             # LLM 对话模块
│   └── main.py             # 主入口
└── tests/                  # 单元测试
```

## 使用方法

启动后通过自然语言与助手对话：

```
你: 我刚订阅了QQ音乐会员，支付宝每月12元，账号QQ号12800
助手: ✅ 已添加订阅：QQ音乐会员

你: 帮我查一下当前有哪些订阅
助手: | 服务名称 | 金额 | 周期 | 下次扣款日 | ...

你: 帮我核算一下本月的订阅费总额
助手: 📊 2026-04 月度订阅费用报表 ...
```

### 核心功能

- **增删改查** — 自然语言管理订阅记录
- **智能日期推算** — 自动计算下次扣款日（月付+1月、年付+1年等）
- **扣款提醒** — 提前 3 天提醒，每小时检查，确认后停止
- **月度报表** — 月末自动生成，支持多币种汇总
- **永久会员** — 买断制订阅统一管理

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feat/your-feature`)
3. 提交更改 (`git commit -m 'feat: add your feature'`)
4. 推送分支 (`git push origin feat/your-feature`)
5. 发起 Pull Request

## 许可证

MIT — 详见 [LICENSE](LICENSE)。

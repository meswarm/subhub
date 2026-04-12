# service.subhub 命令说明

> 系统类型：HTTP API 服务 + 主动 webhook 提醒

---

## 启动方式

```bash
uv run subhub
```

启动 HTTP API 服务。若已配置 [webhook]，同一进程会同时启用主动提醒推送。

监听地址默认读取 `config.toml` 中的 `[server]` 配置，例如：

```toml
[server]
host = "127.0.0.1"
port = 58000
```

也可通过 `--host` / `--port` 临时覆盖。

常用接口示例：

```bash
curl http://127.0.0.1:58000/api/subscriptions

curl -X POST http://127.0.0.1:58000/api/subscriptions \
	-H "Content-Type: application/json" \
	-d '{"name":"Netflix","account":"test@gmail.com","payment_channel":"visa","amount":15.99,"currency":"USD","billing_cycle":"monthly","next_billing_date":"2026-05-01","notes":""}'

curl -X POST http://127.0.0.1:58000/api/subscriptions/delete \
	-H "Content-Type: application/json" \
	-d '{"name":"Netflix"}'

curl "http://127.0.0.1:58000/api/reports/monthly?month=2026-04&mode=budget"
```

---

## 工作目录

```
/home/txl/Code/meswarm/subhub
```

---

## 功能范围

管理个人订阅服务，支持以下操作：

- **新增订阅**：记录服务名称、账号、支付渠道、金额、货币、计费周期、下次扣款日
- **删除订阅**：按名称或 ID 删除
- **修改订阅**：更新任意字段（金额、周期、扣款日等）
- **查询订阅**：列出全部，或按名称模糊搜索、按计费周期筛选
- **生成月报**：月度订阅预算报表（折算月费）或实际扣款报表
- **处理提醒**：用户确认已收到扣款提醒时关闭当天提醒

支持的计费周期：月付、季付、半年付、年付、周付、日付、永久、自定义

支持的货币：CNY、USD、EUR、GBP、JPY

---

## 输出格式

- 接口返回 JSON，编码 UTF-8
- 成功响应格式：`{"ok": true, "data": ...}`
- 失败响应格式：`{"ok": false, "error": {"code": "...", "message": "..."}}`

---

## 主动事件

本系统有主动提醒需求。启动 API 服务后，如已配置 [webhook]，检测到即将扣款的订阅时会直接推送文本到 Link webhook：

```
POST http://127.0.0.1:9001/alert
{"message": "<提醒内容>"}
```

提醒规则：提前 3 天，每 1 小时检查一次（可配置）。

---

## 特殊注意事项

- 默认监听地址为 `127.0.0.1:8000`
- 数据存储在本地 JSON 文件，路径由 `config.toml` 中 `[data]` 决定

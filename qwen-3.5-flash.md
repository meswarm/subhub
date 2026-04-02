SDK 调用配置的base_url：https://dashscope.aliyuncs.com/compatible-mode/v1

HTTP 请求地址：POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions


## 文本输入
```python

import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

completion = client.chat.completions.create(
    # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    model="qwen-plus",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "你是谁？"},
    ]
)
print(completion.model_dump_json())

```


## 工具调用
```python
import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 填写DashScope SDK的base_url
)

tools = [
    # 工具1 获取当前时刻的时间
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "当你想知道现在的时间时非常有用。",
            "parameters": {}  # 因为获取当前时间无需输入参数，因此parameters为空字典
        }
    },  
    # 工具2 获取指定城市的天气
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "当你想查询指定城市的天气时非常有用。",
            "parameters": {  
                "type": "object",
                "properties": {
                    # 查询天气时需要提供位置，因此参数设置为location
                    "location": {
                        "type": "string",
                        "description": "城市或县区，比如北京市、杭州市、余杭区等。"
                    }
                },
                "required": ["location"]
            }
        }
    }
]
messages = [{"role": "user", "content": "杭州天气怎么样"}]
completion = client.chat.completions.create(
    model="qwen-plus",  # 此处以qwen-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    messages=messages,
    tools=tools
)

print(completion.model_dump_json())

```

## 联网搜索
```python

import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key=os.getenv("DASHSCOPE_API_KEY"), 
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
completion = client.chat.completions.create(
    model="qwen-plus",  # 此处以qwen-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    messages=[
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': '中国队在巴黎奥运会获得了多少枚金牌'}],
    extra_body={
        "enable_search": True
    }
    )
print(completion.model_dump_json())
```


# 千问 API 请求体参数说明（OpenAI 兼容格式）

## 一、基础必选参数
### `model` (string, 必选)
模型名称。
- 支持：Qwen 大语言模型（商业版、开源版）、Qwen-VL、Qwen-Coder、Qwen-Omni、Qwen-Math
- Qwen-Audio 不支持 OpenAI 兼容协议，仅支持 DashScope 协议
- 具体模型与计费：参见「文本生成-千问」

### `messages` (array, 必选)
对话上下文，按顺序排列。

---

## 二、消息对象类型

### 1. System Message (object, 可选)
系统提示，一般放在首位。
- **QwQ 不建议设置**
- **QVQ 设置不生效**

属性：
- `content` (string, 必选)：系统指令
- `role` (string, 必选)：固定为 `system`

### 2. User Message (object, 必选)
用户输入。

属性：
- `content` (string | array, 必选)
  - 纯文本：string
  - 多模态/显式缓存：array
- `role` (string, 必选)：固定为 `user`

### 3. Assistant Message (object, 可选)
模型回复（用于多轮上下文）。

属性：
- `content` (string, 可选)：回复文本（有 `tool_calls` 时可为空）
- `role` (string, 必选)：固定为 `assistant`
- `partial` (boolean, 可选, default: `false`)：是否前缀续写
- `tool_calls` (array, 可选)：Function Calling 工具调用信息

### 4. Tool Message (object, 可选)
工具执行结果。

属性：
- `content` (string, 必选)：工具输出（需序列化为字符串）
- `role` (string, 必选)：固定为 `tool`
- `tool_call_id` (string, 必选)：对应 `tool_calls.id`

---

## 三、输出控制参数

### `stream` (boolean, 可选, default: `false`)
流式输出。
- `true`：边生成边返回
- `false`：全量返回
- 推荐 `true`，降低超时风险

### `stream_options` (object, 可选)
仅 `stream=true` 生效。
- `include_usage` (boolean, optional, default: `false`)：最后一块返回 Token 用量

### `modalities` (array, 可选, default: `["text"]`)
仅 Qwen-Omni。
- `["text"]` / `["text","audio"]`

### `audio` (object, 可选)
仅 Qwen-Omni + `modalities=["text","audio"]`。
- `voice` (string, 必选)：音色
- `format` (string, 必选)：固定 `wav`

---

## 四、生成随机性参数

### `temperature` (float, 可选)
采样温度 `[0, 2)`，越高越随机。
- 与 `top_p` 二选一
- QVQ 不建议改默认

### `top_p` (float, 可选)
核采样 `(0,1.0]`，越高越随机。
- 与 `temperature` 二选一
- QVQ 不建议改默认

### `top_k` (integer, 可选)
候选 Token 数，≥0。
- 非 OpenAI 标准，Python SDK 放入 `extra_body`
- QVQ 不建议改默认

### `repetition_penalty` (float, 可选)
重复惩罚，>0，1.0 无惩罚。
- 非 OpenAI 标准，放入 `extra_body`
- qwen-vl-plus_2025-01-25 文字提取建议 `1.0`
- QVQ 不建议改默认

### `presence_penalty` (float, 可选)
内容重复度 `[-2.0, 2.0]`。
- 正值降重复，负值增重复
- qwen-vl-plus-2025-01-25 文字提取建议 `1.5`
- QVQ 不建议改默认

---

## 五、格式与长度

### `response_format` (object, 可选, default: `{"type":"text"}`)
- `{"type":"text"}`
- `{"type":"json_object"}`：需提示词明确 JSON

### `max_tokens` (integer, 可选)
最大输出 Token 数，超则 `finish_reason="length"`。

---

## 六、多模态图像

### `vl_high_resolution_images` (boolean, 可选, default: `false`)
高分辨率图像开关。
- 非 OpenAI 标准，放入 `extra_body`

---

## 七、多候选与思考

### `n` (integer, 可选, default: `1`)
生成候选数 1–4。
- 仅 Qwen3（非思考）、qwen-plus-character
- 有 `tools` 时必须 `n=1`

### `enable_thinking` (boolean, 可选)
思考模式（Qwen3.6/3.5/3/VL/Omni-Flash）。
- 非 OpenAI 标准，放入 `extra_body`

### `preserve_thinking` (boolean, 可选, default: `false`)
保留历史 `reasoning_content`。
- 仅 qwen3.6-plus/2026-04-02
- 计入 Token 计费

### `thinking_budget` (integer, 可选)
思考最大 Token 数。
- 非 OpenAI 标准，放入 `extra_body`

---

## 八、工具与搜索

### `tools` (array, 可选)
Function Calling 工具列表。

### `tool_choice` (string | object, 可选, default: `auto`)
- `auto` / `none` / `{"type":"function","function":{"name":xxx}}`
- 思考模型不支持强制指定函数

### `parallel_tool_calls` (boolean, 可选, default: `false`)
并行工具调用。

### `enable_search` (boolean, 可选, default: `false`)
联网搜索。
- 非 OpenAI 标准，放入 `extra_body`

### `search_options` (object, 可选)
搜索策略配置。
- 非 OpenAI 标准，放入 `extra_body`

---

## 九、其他

### `enable_code_interpreter` (boolean, 可选, default: `false`)
代码解释器。
- 非 OpenAI 标准，放入 `extra_body`

### `seed` (integer, 可选)
随机种子，用于可复现生成 `[0, 2^31-1]`。

### `logprobs` (boolean, 可选, default: `false`)
返回 Token 对数概率。

### `top_logprobs` (integer, 可选, default: `0`)
每步返回候选数 `[0,5]`，仅 `logprobs=true` 生效。

### `stop` (string | array, 可选)
停止词/ID，不可混合字符串与 ID。

---

## 十、请求头（非请求体）

### `X-DashScope-DataInspection` (string, 可选)
输入输出安全增强识别。
- `'{"input":"cip","output":"cip"}'`
- HTTP Header / Python `extra_headers`
- Node.js SDK 不支持
[![English](https://img.shields.io/badge/English-README-blue)](README.md)[![中文](https://img.shields.io/badge/中文-README-red)](README\_CN.md)

# 语义工具选择器 (Retrieval Tool Selector)

[![Python 版本](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyPI 版本](https://img.shields.io/pypi/v/retrieval-tool-selector.svg)](https://pypi.org/project/retrieval-tool-selector/)
[![许可证: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

基于语义嵌入的智能工具选择器，通过自然语言理解自动匹配用户查询与API功能。本库可显著减少大语言模型的幻觉问题，提升函数调用准确率：

1. **精准匹配**：通过语义相似度识别最相关的API功能
2. **参数过滤**：根据查询上下文智能筛选枚举参数
3. **零样本学习**：无需训练即可使用OpenAI嵌入模型

## 功能特性

- 🔍 自然语言查询与API函数的语义匹配
- 🎯 基于上下文的参数枚举值动态过滤
- ⚡ 预计算嵌入向量实现快速推理
- 🧠 支持多种嵌入模型（Ada、Cohere、text-embedding-3等）
- 📊 内置相似度分析调试输出
- 🔄 兼容OpenAI函数调用范式

## 安装方法

```bash
pip install retrieval-tool-selector
```


## 快速开始

```
from retrieval_tool_selector import RetrievalAugmentedToolSelector

# 定义工具列表（OpenAI函数调用格式）
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取当前天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "城市名称"},
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit", "kelvin"],
                        "description": "温度单位"
                    },
                    "forecast_type": {
                        "type": "string",
                        "enum": ["current", "hourly", "daily", "weekly"],
                        "description": "预报时间范围"
                    }
                },
                "required": ["location"]
            }
        }
    }
]

# 初始化选择器
selector = RetrievalAugmentedToolSelector(
    tools=tools,
    api_key="您的OpenAI_API密钥",
    base_url="https://api.openai.com/v1",  # 可使用Azure或其他兼容端点
    embedding_model="text-embedding-3-small"
)

# 处理用户查询
query = "东京未来24小时天气预报"
selected_tools = selector.select_tools(
    query,
    tool_threshold=0.65,  # 工具相似度阈值
    tool_top_k=1,          # 最多返回工具数
    enum_threshold=0.5,    # 枚举值相似度阈值
    enum_top_k=2           # 每个参数最多保留枚举值数
)

print(selected_tools)
```

## 核心原理

### 工作流程

1. **预处理阶段**：
   * 为所有工具名称和描述生成嵌入向量
   * 为所有枚举参数值生成嵌入向量
2. **查询处理**：
   * 计算查询语句的嵌入向量
   * 通过余弦相似度匹配最相关工具
   * 根据语义相关性筛选枚举参数
3. **输出结果**：返回过滤后的工具定义，可直接供大语言模型使用

### 关键参数


| 参数             | 默认值 | 说明                         |
| ---------------- | ------ | ---------------------------- |
| `tool_threshold` | 0.7    | 工具匹配的最低相似度要求     |
| `tool_top_k`     | 1      | 最多返回的工具数量           |
| `enum_threshold` | 0.6    | 枚举值保留的最低相似度       |
| `enum_top_k`     | 3      | 每个参数保留的最大枚举值数量 |

### 支持模型

可兼容任何OpenAI API支持的嵌入模型：

* `text-embedding-ada-002` (默认)
* `text-embedding-3-small`
* `text-embedding-3-large`
* 或其他兼容的自定义模型

## 高级应用

### 与OpenAI聊天补全集成

```
from openai import OpenAI

# 初始化工具选择器
selector = RetrievalAugmentedToolSelector(tools, api_key, base_url)

# 处理用户查询
query = "显示巴黎未来一周的摄氏温度预报"
selected_tools = selector.select_tools(query)

# 调用OpenAI接口
client = OpenAI(api_key=api_key, base_url=base_url)
response = client.chat.completions.create(
    model="gpt-4-turbo",
    messages=[{"role": "user", "content": query}],
    tools=selected_tools,
    tool_choice="auto"
)
```

### 枚举值语义映射

当枚举值为代码但需要语义匹配时：

```
{
    "type": "string",
    "enum": ["USD", "EUR", "JPY"],
    "enum_semantic": ["美元", "欧元", "日元"]  # 用于生成嵌入向量
}
```

### 调试输出示例

```
工具相似度分析:
嵌入模型: text-embedding-3-large
  - get_weather: 0.8723
  - get_stock: 0.5121

枚举过滤结果 (阈值=0.5, 最多保留2个):
  原始值: ['current', 'hourly', 'daily', 'weekly']
  过滤后: ['hourly', 'daily']
```

## 典型应用场景

1. **智能客服**：将自然语言转换为精准API调用
2. **数据接口**：处理多枚举值参数（如国家代码、产品类型）
3. **API网关**：自动路由请求到对应服务
4. **RAG系统**：作为检索增强生成的关键组件
5. **低代码平台**：提升自然语言配置的准确性

## 最佳实践

1. 初期使用`text-embedding-3-small`控制成本
2. 根据工具多样性调整相似度阈值
3. 对多值参数设置更高的top\_k
4. 编写详细的工具描述提升匹配精度
5. 使用多样化查询语句进行测试

## 注意事项

* 需要调用OpenAI API生成嵌入向量
* 主要面向文本型工具（可扩展至多模态）
* 枚举值需具有明确语义时效果最佳

## 参与贡献

欢迎提交Pull Request或Issue至[GitHub仓库](https://github.com/xiaoyesoso/retrieval-tool-selector)

## 开源协议

本项目采用MIT许可证 - 详见[LICENSE](https://yuanbao.tencent.com/chat/naQivTmsDa/LICENSE)文件

---

开发团队：SoulJoy（卓寿杰）

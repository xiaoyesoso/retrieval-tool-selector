[![English](https://img.shields.io/badge/English-README-blue)](README.md)[![中文](https://img.shields.io/badge/中文-README-red)](README\_CN.md)

# Retrieval Tool Selector

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyPI Version](https://img.shields.io/pypi/v/retrieval-tool-selector.svg)](https://pypi.org/project/retrieval-tool-selector/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A retrieval-augmented tool selector that uses semantic embeddings to dynamically match user queries to relevant API functions and parameters. This library helps reduce LLM hallucination and improve function calling accuracy by:

1. **Tool Selection**: Identifying the most relevant API functions using semantic similarity
2. **Parameter Filtering**: Intelligently filtering enum parameters based on query context
3. **Zero-shot Retrieval**: Working with no prior training using OpenAI's embedding models

## Features

- 🔍 Semantic matching between natural language queries and API functions
- 🎯 Context-aware filtering of parameter enums
- ⚡ Precomputed embeddings for fast inference
- 🧠 Support for different embedding models (Ada, Cohere, text-embedding-3, etc.)
- 📊 Built-in debug outputs for similarity analysis
- 🔄 Compatible with OpenAI function calling paradigm

## Installation

```bash
pip install retrieval-tool-selector
```

## Quick Start

```python
from retrieval_tool_selector import RetrievalAugmentedToolSelector

# Define your tools in OpenAI function-calling format
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather information",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"},
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit", "kelvin"]
                    },
                    "forecast_type": {
                        "type": "string",
                        "enum": ["current", "hourly", "daily", "weekly"]
                    }
                },
                "required": ["location"]
            }
        }
    }
]

# Initialize selector
selector = RetrievalAugmentedToolSelector(
    tools=tools,
    api_key="your_openai_api_key",
    base_url="https://api.openai.com/v1",  # Can use Azure or other compatible endpoints
    embedding_model="text-embedding-3-small"
)

# Select tools based on user query
query = "What's the hourly forecast for Tokyo?"
selected_tools = selector.select_tools(
    query,
    tool_threshold=0.65,
    tool_top_k=1,
    enum_threshold=0.5,
    enum_top_k=2
)

print(selected_tools)
```

## Key Concepts

### Tool Selection Workflow

1. **Precomputation**: During initialization, embeddings are generated for:
   - All tool names and descriptions
   - All enum parameter values
2. **Query Processing**: For each user query:
   - Compute query embedding
   - Compare against tool embeddings to find matches
   - Filter enum parameters based on semantic relevance
3. **Output**: Returns tool definitions with filtered parameters ready for LLM consumption

### Configuration Parameters


| Parameter        | Default | Description                                         |
| ---------------- | ------- | --------------------------------------------------- |
| `tool_threshold` | 0.7     | Minimum cosine similarity for tool selection        |
| `tool_top_k`     | 1       | Maximum number of tools to return                   |
| `enum_threshold` | 0.6     | Minimum cosine similarity for enum inclusion        |
| `enum_top_k`     | 3       | Maximum number of enum values to keep per parameter |

### Supported Embedding Models

You can use any embedding model supported by your OpenAI-compatible API:

- `text-embedding-ada-002` (default)
- `text-embedding-3-small`
- `text-embedding-3-large`
- Or any custom models supported by your endpoint

## Advanced Usage

### Integrating with OpenAI Chat Completions

```python
from openai import OpenAI

# Initialize tool selector
selector = RetrievalAugmentedToolSelector(tools, api_key, base_url)

# Process user query
query = "Show me the weekly weather forecast for Paris in Celsius"
selected_tools = selector.select_tools(query)

# Call OpenAI with filtered tools
client = OpenAI(api_key=api_key, base_url=base_url)
response = client.chat.completions.create(
    model="gpt-4-turbo",
    messages=[{"role": "user", "content": query}],
    tools=selected_tools,
    tool_choice="auto"
)
```

### Handling Enum Value Mismatches

If your enum values use special formats but need semantic matching:

```python
# During tool definition, add semantic equivalents:
{
    "type": "string",
    "enum": ["USD", "EUR", "JPY"],
    "enum_semantic": ["US Dollar", "Euro", "Japanese Yen"]
}
```

Then modify the tool preprocessing step to use semantic equivalents for embedding generation.

### Debugging Similarity Scores

The library provides debug outputs:

```
Tool similarity analysis:
Embedding model: text-embedding-3-large
  - get_weather: 0.8723
  - get_stock: 0.5121

Enum filtering results (threshold=0.5, top_k=2):
  Original: ['current', 'hourly', 'daily', 'weekly']
  Filtered: ['hourly', 'daily']
```

## Use Cases

1. **Function Calling**: Improve tool selection accuracy for LLMs
2. **API Gateways**: Automatically route requests to appropriate services
3. **Conversational Interfaces**: Parse natural language into precise API calls
4. **Data APIs**: Handle enums with many possible values (e.g. country codes, product types)
5. **RAG Systems**: As a component in larger retrieval-augmented generation pipelines

## Best Practices

1. Start with `text-embedding-3-small` for cost efficiency
2. Adjust thresholds based on your tool diversity
3. Use higher top_k for parameters with many possible values
4. Include detailed tool descriptions for better matching
5. Test with diverse query phrasings

## Limitations

- Requires OpenAI API calls for embedding generation
- Primarily designed for text-based tools (though could extend to multimodal)
- Enum filtering works best when values have clear semantic meaning

## Contributing

Contributions are welcome! Please submit pull requests or open issues on [GitHub](https://github.com/xiaoyesoso/retrieval-tool-selector).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

Developed by SoulJoy（卓寿杰）

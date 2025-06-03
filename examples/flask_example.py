import os
import json
from flask import Flask, request, jsonify
from openai import OpenAI
from retrieval_tool_selector import RetrievalAugmentedToolSelector
from typing import Dict, Any, List, Optional

app = Flask(__name__)


class Config:
    """Configuration settings for the service"""

    # Service configuration
    SERVICE_PORT = int(os.getenv("PORT", "5000"))
    DEBUG_MODE = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

    # OpenAI client configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_api_key")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_DEFAULT_MODEL = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4-turbo")

    # Embedding model for tool selection
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    # Tool selector thresholds
    TOOL_THRESHOLD = float(os.getenv("TOOL_THRESHOLD", "0.65"))
    TOOL_TOP_K = int(os.getenv("TOOL_TOP_K", "3"))
    ENUM_THRESHOLD = float(os.getenv("ENUM_THRESHOLD", "0.55"))
    ENUM_TOP_K = int(os.getenv("ENUM_TOP_K", "2"))

    # API tool definitions
    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current and forecast weather data",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "City or region name"},
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "Temperature unit system"
                        },
                        "forecast_type": {
                            "type": "string",
                            "enum": ["current", "hourly", "daily"],
                            "description": "Type of weather forecast"
                        }
                    },
                    "required": ["location"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_financial_data",
                "description": "Retrieve stock prices and financial information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Stock ticker symbol"},
                        "exchange": {
                            "type": "string",
                            "enum": ["NYSE", "NASDAQ", "HKEX", "SSE"],
                            "description": "Stock exchange market"
                        },
                        "period": {
                            "type": "string",
                            "enum": ["1d", "1w", "1m", "3m", "1y"],
                            "description": "Time period for data"
                        }
                    },
                    "required": ["symbol"]
                }
            }
        }
    ]


# Initialize OpenAI client
openai_client = OpenAI(
    api_key=Config.OPENAI_API_KEY,
    base_url=Config.OPENAI_BASE_URL
)

# Initialize tool selector at startup
tool_selector = RetrievalAugmentedToolSelector(
    tools=Config.TOOLS,
    api_key=Config.OPENAI_API_KEY,
    base_url=Config.OPENAI_BASE_URL,
    embedding_model=Config.EMBEDDING_MODEL
)
print(f"Tool selector initialized with {len(Config.TOOLS)} tools")


def process_message(messages: List[Dict[str, str]]) -> Optional[str]:
    """
    Extract the most recent user message from conversation history
    Returns None if no user message found
    """
    # Traverse messages in reverse to find the latest user message
    for message in reversed(messages):
        if message.get("role") == "user":
            return message.get("content")
    return None


def enhance_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhance the OpenAI request payload with tool selection
    while preserving all original parameters
    """
    payload = payload.copy()  # Don't modify original

    # Get the most recent user message
    user_query = process_message(payload.get("messages", []))

    # Only proceed if we have a query to process
    if not user_query:
        return payload

    # Select tools based on user query
    selected_tools = tool_selector.select_tools(
        user_query,
        tool_threshold=Config.TOOL_THRESHOLD,
        tool_top_k=Config.TOOL_TOP_K,
        enum_threshold=Config.ENUM_THRESHOLD,
        enum_top_k=Config.ENUM_TOP_K
    )

    if Config.DEBUG_MODE:
        print(f"Selected {len(selected_tools)} tool(s) for query: '{user_query}'")

    # Add selected tools to request payload
    payload["tools"] = selected_tools

    # Set tool choice to "auto" unless explicitly defined
    if "tool_choice" not in payload:
        payload["tool_choice"] = "auto"

    return payload


def create_completion_response(openai_response: Dict) -> Dict:
    """
    Transform OpenAI API response to match their SDK object serialization
    """
    # Handle both ChatCompletion and ChatCompletionChunk formats
    choices = []
    for choice in openai_response.get("choices", []):
        message = choice.get("message", {})
        tool_calls = []

        # Process tool calls if present
        for tool_call in message.get("tool_calls", []):
            func = tool_call.get("function", {})
            tool_calls.append({
                "id": tool_call.get("id"),
                "type": "function",
                "function": {
                    "name": func.get("name"),
                    "arguments": func.get("arguments")
                }
            })

        choices.append({
            "finish_reason": choice.get("finish_reason"),
            "index": choice.get("index"),
            "message": {
                "content": message.get("content"),
                "role": message.get("role"),
                "tool_calls": tool_calls or None
            }
        })

    # Construct full response
    return {
        "id": openai_response.get("id", "chatcmpl-" + os.urandom(8).hex()),
        "object": "chat.completion",
        "created": openai_response.get("created", int(time.time())),
        "model": openai_response.get("model", Config.OPENAI_DEFAULT_MODEL),
        "choices": choices,
        "usage": openai_response.get("usage", {})
    }


@app.route('/v1/chat/completions', methods=['POST'])
def chat_completion():
    """
    OpenAI-compatible chat completion endpoint with semantic tool selection

    Request format: https://platform.openai.com/docs/api-reference/chat/create
    Response format: https://platform.openai.com/docs/api-reference/chat/object
    """
    try:
        # Get and validate request payload
        payload = request.get_json()
        if not payload or "messages" not in payload:
            return jsonify({
                "error": {
                    "message": "Invalid request: missing 'messages' parameter",
                    "type": "invalid_request_error"
                }
            }), 400

        # Enhance request with tool selection
        enhanced_payload = enhance_request(payload)

        if Config.DEBUG_MODE:
            print("Enhanced request payload:", json.dumps(enhanced_payload, indent=2))

        # Call OpenAI API with enhanced request
        response = openai_client.chat.completions.create(**enhanced_payload)

        # Serialize response and return
        return jsonify(response.to_dict())

    except Exception as e:
        return jsonify({
            "error": {
                "message": f"Processing error: {str(e)}",
                "type": "server_error"
            }
        }), 500


if __name__ == '__main__':
    import time

    print(f"Starting API server on port {Config.SERVICE_PORT}")
    app.run(host='0.0.0.0', port=Config.SERVICE_PORT)
import json
from typing import Optional
from httpx import AsyncClient
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMResponse:
    content: str
    model: str
    tokens_used: int


class OllamaClient:
    def __init__(self, model: str, base_url: str, max_tokens: int):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens

    async def invoke(self, messages: list[dict]) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": self.max_tokens,
            },
        }
        async with AsyncClient(timeout=120) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            result = LLMResponse()
            result.content = data["message"]["content"]
            result.model = data.get("model", self.model)
            eval_count = data.get("eval_count", 0)
            result.tokens_used = eval_count if eval_count else 0
            return result


class GrokClient:
    """OpenAI-compatible client (xAI Grok, Groq, etc.)."""

    def __init__(self, model: str, api_key: str, base_url: str, max_tokens: int):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens

    async def invoke(self, messages: list[dict]) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": 0.1,
        }
        async with AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "content-type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            result = LLMResponse()
            result.content = choice["message"]["content"]
            result.model = data.get("model", self.model)
            usage = data.get("usage", {})
            result.tokens_used = usage.get("total_tokens", 0)
            return result


class AnthropicClient:
    def __init__(self, model: str, api_key: str, max_tokens: int):
        self.model = model
        self.api_key = api_key
        self.max_tokens = max_tokens

    async def invoke(self, messages: list[dict]) -> LLMResponse:
        system_msg = None
        api_messages = []
        for m in messages:
            if m.get("role") == "system":
                system_msg = m["content"]
            else:
                api_messages.append({"role": m["role"], "content": m["content"]})

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": api_messages,
        }
        if system_msg:
            payload["system"] = system_msg

        async with AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            result = LLMResponse()
            result.content = "".join(
                block["text"] for block in data["content"] if block["type"] == "text"
            )
            result.model = data.get("model", self.model)
            usage = data.get("usage", {})
            result.tokens_used = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
            return result


_client: Optional[object] = None


def get_llm():
    global _client
    if _client is not None:
        return _client

    settings = get_settings()
    provider = settings.LLM_PROVIDER

    if provider == "ollama":
        _client = OllamaClient(settings.LLM_MODEL, settings.OLLAMA_BASE_URL, settings.ANTHROPIC_MAX_TOKENS)
    elif provider == "grok":
        if not settings.GROK_API_KEY:
            raise ValueError("GROK_API_KEY is required when LLM_PROVIDER=grok")
        _client = GrokClient(settings.GROK_MODEL, settings.GROK_API_KEY, settings.GROK_BASE_URL, settings.ANTHROPIC_MAX_TOKENS)
    elif provider == "groq":
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is required when LLM_PROVIDER=groq")
        _client = GrokClient(settings.GROQ_MODEL, settings.GROQ_API_KEY, settings.GROQ_BASE_URL, settings.ANTHROPIC_MAX_TOKENS)
    elif provider == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
        _client = AnthropicClient(
            settings.ANTHROPIC_MODEL or "claude-sonnet-4-20250514",
            settings.ANTHROPIC_API_KEY,
            settings.ANTHROPIC_MAX_TOKENS,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    logger.info(f"LLM client created: provider={provider}")
    return _client


async def llm_invoke(messages: list[dict]) -> LLMResponse:
    client = get_llm()
    return await client.invoke(messages)

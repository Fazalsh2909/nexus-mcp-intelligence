from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import json

from app.core.config import settings


class LLMProvider(ABC):
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        pass


class OpenAIProvider(LLMProvider):
    def __init__(self):
        import openai

        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        kwargs = {
            "model": settings.LLM_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        usage = getattr(response, "usage", None)
        usage_payload = None
        if usage:
            usage_payload = {
                "input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                "output_tokens": getattr(usage, "completion_tokens", 0) or 0,
            }

        if choice.message.tool_calls:
            return {
                "tool_calls": [
                    {
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in choice.message.tool_calls
                ],
                "usage": usage_payload,
            }

        return {"content": choice.message.content or "", "usage": usage_payload}


class GroqProvider(LLMProvider):
    def __init__(self):
        import openai

        self.client = openai.AsyncOpenAI(
            base_url=settings.GROQ_BASE_URL,
            api_key=settings.GROQ_API_KEY,
        )
        self.model = settings.LLM_MODEL

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        if choice.message.tool_calls:
            return {
                "tool_calls": [
                    {
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in choice.message.tool_calls
                ]
            }

        return {"content": choice.message.content or ""}


class OpenRouterProvider(LLMProvider):
    def __init__(self):
        import openai

        self.client = openai.AsyncOpenAI(
            base_url=settings.OPENROUTER_BASE_URL,
            api_key=settings.OPENROUTER_API_KEY,
        )
        self.model = settings.LLM_MODEL

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        usage = getattr(response, "usage", None)
        usage_payload = None
        if usage:
            usage_payload = {
                "input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                "output_tokens": getattr(usage, "completion_tokens", 0) or 0,
            }

        if choice.message.tool_calls:
            return {
                "tool_calls": [
                    {
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in choice.message.tool_calls
                ],
                "usage": usage_payload,
            }

        return {"content": choice.message.content or "", "usage": usage_payload}


class AnthropicProvider(LLMProvider):
    def __init__(self):
        import anthropic

        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        system_msg = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                chat_messages.append(msg)

        kwargs = {
            "model": settings.LLM_MODEL,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_msg:
            kwargs["system"] = system_msg
        if tools:
            kwargs["tools"] = [
                {
                    "name": t["function"]["name"],
                    "description": t["function"].get("description", ""),
                    "input_schema": t["function"].get("parameters", {}),
                }
                for t in tools
            ]

        response = await self.client.messages.create(**kwargs)

        if response.stop_reason == "tool_use":
            tool_calls = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_calls.append(
                        {
                            "id": block.id,
                            "function": {
                                "name": block.name,
                                "arguments": json.dumps(block.input),
                            },
                        }
                    )
            return {"tool_calls": tool_calls}

        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text

        usage_payload = None
        usage = getattr(response, "usage", None)
        if usage:
            usage_payload = {
                "input_tokens": getattr(usage, "input_tokens", 0) or 0,
                "output_tokens": getattr(usage, "output_tokens", 0) or 0,
            }
        return {"content": content, "usage": usage_payload}


def get_llm_provider() -> LLMProvider:
    if settings.LLM_PROVIDER == "openrouter":
        return OpenRouterProvider()
    elif settings.LLM_PROVIDER == "groq":
        return GroqProvider()
    elif settings.LLM_PROVIDER == "anthropic":
        return AnthropicProvider()
    return OpenAIProvider()

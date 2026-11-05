"""Thin LLM abstraction.

Every node asks for a *typed* result (a Pydantic model). Hiding the provider
behind this small interface keeps nodes provider-agnostic and lets tests swap
in a deterministic fake without network calls.
"""

from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.config import get_settings

T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    def structured(self, system: str, user: str, schema: type[T]) -> T: ...


class OpenAIClient:
    def __init__(self, model: str | None = None, temperature: float | None = None):
        from langchain_openai import ChatOpenAI

        s = get_settings()
        if not s.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Copy .env.example to .env and add it.")
        self._chat = ChatOpenAI(
            model=model or s.openai_model,
            temperature=s.openai_temperature if temperature is None else temperature,
            api_key=s.openai_api_key,
            max_retries=3,
            timeout=60,
        )

    def structured(self, system: str, user: str, schema: type[T]) -> T:
        runnable = self._chat.with_structured_output(schema, method="json_schema", strict=False)
        result = runnable.invoke([("system", system), ("human", user)])
        if isinstance(result, dict):  # some providers return dicts
            result = schema.model_validate(result)
        return result  # type: ignore[return-value]


_client: LLMClient | None = None


def get_llm() -> LLMClient:
    global _client
    if _client is None:
        _client = OpenAIClient()
    return _client


def set_llm(client: LLMClient | None) -> None:
    """Override the global client (used by tests and evals)."""
    global _client
    _client = client

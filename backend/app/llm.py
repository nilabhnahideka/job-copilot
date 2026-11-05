"""Thin LLM abstraction.

Every node asks for a *typed* result (a Pydantic model). Hiding the provider
behind this small interface keeps nodes provider-agnostic and lets tests swap
in a deterministic fake without network calls.

Providers (choose with LLM_PROVIDER in .env):
- "gemini": Google Gemini. Has a free tier (no card needed); get a key at
  https://aistudio.google.com/apikey. Note: on the free tier Google may use
  what you send to improve its products.
- "openai": OpenAI. Pay-as-you-go; key from https://platform.openai.com/api-keys.

Check your key works with:  python -m app.llm check
"""

from __future__ import annotations

import sys
from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.config import Settings, get_settings

T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    def structured(self, system: str, user: str, schema: type[T]) -> T: ...


class LangChainClient:
    """Wraps any LangChain chat model that supports structured output."""

    def __init__(self, chat):
        self._chat = chat

    def structured(self, system: str, user: str, schema: type[T]) -> T:
        runnable = self._chat.with_structured_output(schema, method="json_schema")
        result = runnable.invoke([("system", system), ("human", user)])
        if isinstance(result, dict):  # some providers return dicts
            result = schema.model_validate(result)
        if result is None:  # the model replied without valid JSON
            raise RuntimeError(f"The AI didn't return a valid {schema.__name__}. Try again.")
        return result  # type: ignore[return-value]


def build_client(s: Settings) -> LangChainClient:
    """Create the client for the provider chosen in settings."""
    if s.llm_provider == "gemini":
        if not s.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Get a free key at https://aistudio.google.com/apikey "
                "and add it to backend/.env"
            )
        from langchain_google_genai import ChatGoogleGenerativeAI

        chat = ChatGoogleGenerativeAI(
            model=s.gemini_model,
            google_api_key=s.gemini_api_key,
            temperature=s.llm_temperature,
            # The free tier allows only a few requests per minute; retry instead of failing.
            max_retries=6,
            timeout=120,
        )
        return LangChainClient(chat)

    if s.llm_provider == "openai":
        if not s.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to backend/.env")
        from langchain_openai import ChatOpenAI

        chat = ChatOpenAI(
            model=s.openai_model,
            temperature=s.llm_temperature,
            api_key=s.openai_api_key,
            max_retries=3,
            timeout=60,
        )
        return LangChainClient(chat)

    raise RuntimeError(f"Unknown LLM_PROVIDER {s.llm_provider!r}. Use 'gemini' or 'openai'.")


_client: LLMClient | None = None


def get_llm() -> LLMClient:
    global _client
    if _client is None:
        _client = build_client(get_settings())
    return _client


def set_llm(client: LLMClient | None) -> None:
    """Override the global client (used by tests and evals)."""
    global _client
    _client = client


# ---------------------------------------------------------------------------
# `python -m app.llm check`: one tiny real request, to confirm your key works.
# ---------------------------------------------------------------------------
class _Ping(BaseModel):
    reply: str


def check() -> int:
    s = get_settings()
    model = s.gemini_model if s.llm_provider == "gemini" else s.openai_model
    print(f"Provider: {s.llm_provider}   Model: {model}")
    try:
        result = build_client(s).structured("Reply with the single word: pong", "ping", _Ping)
    except Exception as e:  # show the provider's message, it usually says what's wrong
        print(f"\nNOT WORKING: {e}")
        return 1
    print(f"Model replied: {result.reply!r}\nWORKING: your AI key is set up correctly.")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["check"]:
        sys.exit(check())
    print("Usage: python -m app.llm check")
    sys.exit(2)

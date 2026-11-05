"""Tests for choosing the AI provider. No network: clients are only constructed, never called."""

import pytest
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel

from app import llm
from app.config import Settings


class Answer(BaseModel):
    text: str


def settings(**kw) -> Settings:
    return Settings(_env_file=None, **kw)


def test_gemini_is_the_default_and_reads_either_key_name(monkeypatch):
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "LLM_PROVIDER"):
        monkeypatch.delenv(var, raising=False)
    assert settings().llm_provider == "gemini"

    monkeypatch.setenv("GEMINI_API_KEY", "key-a")
    assert settings().gemini_api_key == "key-a"
    monkeypatch.delenv("GEMINI_API_KEY")
    monkeypatch.setenv("GOOGLE_API_KEY", "key-b")
    assert settings().gemini_api_key == "key-b"


def test_builds_gemini_client_with_chosen_model():
    from langchain_google_genai import ChatGoogleGenerativeAI

    client = llm.build_client(
        settings(llm_provider="gemini", gemini_api_key="k", gemini_model="gemini-3.5-flash-lite")
    )
    assert isinstance(client._chat, ChatGoogleGenerativeAI)
    assert client._chat.model.endswith("gemini-3.5-flash-lite")


def test_builds_openai_client():
    from langchain_openai import ChatOpenAI

    client = llm.build_client(
        settings(llm_provider="openai", openai_api_key="sk-test", openai_model="gpt-4o-mini")
    )
    assert isinstance(client._chat, ChatOpenAI) and client._chat.model_name == "gpt-4o-mini"


def test_missing_key_gives_a_helpful_message(monkeypatch):
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(RuntimeError, match="aistudio.google.com"):
        llm.build_client(settings(llm_provider="gemini"))
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        llm.build_client(settings(llm_provider="openai"))


class _FakeChat:
    """Stands in for a LangChain chat model: returns `reply` from structured output."""

    def __init__(self, reply):
        self.reply = reply
        self.method = None

    def with_structured_output(self, schema, method):
        self.method = method
        return RunnableLambda(lambda messages: self.reply)


def test_structured_accepts_models_and_dicts_and_rejects_empty_replies():
    chat = _FakeChat(Answer(text="hi"))
    assert llm.LangChainClient(chat).structured("s", "u", Answer) == Answer(text="hi")
    assert chat.method == "json_schema"

    assert (
        llm.LangChainClient(_FakeChat({"text": "from dict"})).structured("s", "u", Answer).text == "from dict"
    )

    with pytest.raises(RuntimeError, match="valid Answer"):
        llm.LangChainClient(_FakeChat(None)).structured("s", "u", Answer)


def test_check_command_reports_working_and_not_working(monkeypatch, capsys):
    monkeypatch.setattr(llm, "get_settings", lambda: settings(gemini_api_key="k"))

    monkeypatch.setattr(
        llm, "build_client", lambda s: llm.LangChainClient(_FakeChat(llm._Ping(reply="pong")))
    )
    assert llm.check() == 0
    assert "WORKING" in capsys.readouterr().out

    def broken(s):
        raise RuntimeError("API key not valid")

    monkeypatch.setattr(llm, "build_client", broken)
    assert llm.check() == 1
    assert "NOT WORKING: API key not valid" in capsys.readouterr().out

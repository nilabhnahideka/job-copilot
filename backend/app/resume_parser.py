from __future__ import annotations

import io

from pypdf import PdfReader

from app.agent import prompts
from app.config import get_settings
from app.llm import get_llm
from app.schemas import ResumeProfile


def extract_pdf_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    if not text.strip():
        raise ValueError("Could not extract text from PDF (is it a scanned image?)")
    return text


def parse_resume(raw_text: str) -> ResumeProfile:
    text = raw_text[: get_settings().max_resume_chars]
    return get_llm().structured(prompts.PARSE_RESUME, f"<resume>\n{text}\n</resume>", ResumeProfile)

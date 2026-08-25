import asyncio

import pytest
from pydantic import ValidationError

from app.evaluation import EvaluationInput, EvaluationResult, HeuristicProvider, is_qualified
from app.parsers import extract_resume_text


def text_pdf(text: str) -> bytes:
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream",
    ]
    result = b"%PDF-1.4\n"; offsets = [0]
    for index, item in enumerate(objects, start=1):
        offsets.append(len(result)); result += f"{index} 0 obj\n".encode() + item + b"\nendobj\n"
    xref = len(result); result += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    result += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    return result + f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()


def test_extracts_text_pdf_and_rejects_empty_content():
    assert "Python FastAPI" in extract_resume_text("candidate.pdf", text_pdf("Python FastAPI experience delivery"))
    with pytest.raises(ValueError, match="未能提取"):
        extract_resume_text("empty.pdf", text_pdf(""))


def test_structured_result_and_threshold_boundaries():
    with pytest.raises(ValidationError):
        EvaluationResult(score=101, reason="invalid")
    assert is_qualified(80, 80) is True
    assert is_qualified(84, 85) is False


def test_development_provider_returns_evidence():
    output = asyncio.run(HeuristicProvider().evaluate(EvaluationInput(prompt="评分", requirements=[{"description": "Python FastAPI", "priority": "required"}], resume_text="五年 Python FastAPI 开发经验")))
    assert output.score == 100
    assert output.satisfied[0].evidence

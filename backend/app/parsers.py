import io
from pathlib import Path

from docx import Document
from pypdf import PdfReader


def extract_resume_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif suffix == ".docx":
        document = Document(io.BytesIO(content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    else:
        raise ValueError("仅支持 PDF 和 DOCX 简历")
    cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if len(cleaned) < 20:
        raise ValueError("未能提取足够文本；扫描件或图片型 PDF 暂不支持 OCR")
    return cleaned

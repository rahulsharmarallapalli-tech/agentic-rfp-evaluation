import hashlib
import pymupdf

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 50
MAX_CHARS = 100_000


def extract_pdf(content: bytes) -> dict:
    if not content or len(content) > MAX_BYTES:
        raise ValueError("PDF must be nonempty and at most 10 MB.")
    if not content.startswith(b"%PDF-"):
        raise ValueError("File is not a PDF.")
    try:
        with pymupdf.open(stream=content, filetype="pdf") as doc:
            if doc.needs_pass:
                raise ValueError("Password-protected PDFs are not supported.")
            if not 1 <= len(doc) <= MAX_PAGES:
                raise ValueError("PDF must contain between 1 and 50 pages.")
            pages = [{"page": i + 1, "text": p.get_text("text").strip()} for i, p in enumerate(doc)]
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("PDF could not be read; upload an undamaged PDF.") from exc
    text = "\n\n".join(f"[PAGE {p['page']}]\n{p['text']}" for p in pages)
    if sum(len(p["text"]) for p in pages) < 50:
        raise ValueError("PDF has insufficient selectable text. Scan-only PDFs need OCR first.")
    if len(text) > MAX_CHARS:
        raise ValueError("PDF exceeds the 100,000-character limit; split it before evaluation.")
    warnings = [f"Page {p['page']} contains little text; image-only evidence is not evaluated."
                for p in pages if len(p["text"]) < 30]
    return {"sha256": hashlib.sha256(content).hexdigest(), "page_count": len(pages),
            "pages": pages, "text": text, "warnings": warnings}

import logging
import re

from pypdf import PdfReader


logger = logging.getLogger(__name__)


def normalize_lines(text):
    lines = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if line:
            lines.append(line)
    return lines


def has_usable_text(lines, min_chars=50):
    total_chars = sum(len(line) for line in lines)
    return total_chars >= min_chars


def extract_pdf_text_by_page(pdf_path):
    """Return selectable PDF text lines for each page.

    Empty lists mark pages that should fall back to OCR.
    """
    try:
        reader = PdfReader(pdf_path)
    except Exception as e:
        logger.warning("Direct PDF text extraction failed: %s", e)
        return []

    pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as e:
            logger.warning("Text extraction failed for page %s: %s", page_number, e)
            pages.append([])
            continue

        lines = normalize_lines(text)
        pages.append(lines if has_usable_text(lines) else [])

    return pages

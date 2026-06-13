from io import BytesIO

import fitz
from PIL import Image


def _page_to_image(page, dpi):
    scale = dpi / 72
    matrix = fitz.Matrix(scale, scale)
    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
    return Image.open(BytesIO(pixmap.tobytes("png"))).convert("RGB")


def render_pdf_page(pdf_path, page_number, dpi=300):
    """Render a 1-based PDF page number to a PIL image."""
    with fitz.open(pdf_path) as document:
        if page_number < 1 or page_number > document.page_count:
            raise ValueError(f"Page {page_number} is outside 1-{document.page_count}")
        return _page_to_image(document.load_page(page_number - 1), dpi)


def get_pdf_page_count(pdf_path):
    with fitz.open(pdf_path) as document:
        return document.page_count


def render_pdf_pages(pdf_path, dpi=300):
    """Render every PDF page to PIL images."""
    with fitz.open(pdf_path) as document:
        return [_page_to_image(page, dpi) for page in document]

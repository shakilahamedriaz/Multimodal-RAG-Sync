import logging
from typing import Optional

import fitz  # PyMuPDF >= 1.23 for find_tables()

from app.schemas import ParsedDocument, ParsedPage

logger = logging.getLogger(__name__)


def _matrix_to_markdown(matrix: list[list]) -> str:
    """Convert a table cell matrix (rows × cols) to GitHub-flavored markdown."""
    if not matrix:
        return ""

    rows = [[str(cell or "").strip() for cell in row] for row in matrix]
    if not rows or not rows[0]:
        return ""

    col_count = max(len(r) for r in rows)
    # Pad short rows
    rows = [r + [""] * (col_count - len(r)) for r in rows]

    widths = [max(len(rows[r][c]) for r in range(len(rows))) for c in range(col_count)]
    widths = [max(w, 3) for w in widths]  # min width 3 for markdown separator

    def fmt_row(row: list[str]) -> str:
        cells = [row[c].ljust(widths[c]) for c in range(col_count)]
        return "| " + " | ".join(cells) + " |"

    header = fmt_row(rows[0])
    separator = "| " + " | ".join("-" * w for w in widths) + " |"
    body_lines = [fmt_row(r) for r in rows[1:]]

    parts = [header, separator] + body_lines
    return "\n".join(parts)


class TableAwarePDFParser:
    """PDF parser that extracts text and tables as separate ParsedPage entries.

    Tables are formatted as markdown and tagged with chunk_type='table' so
    page-level chunking can keep them atomic.
    """

    def parse(self, content: bytes) -> ParsedDocument:
        doc = fitz.open(stream=content, filetype="pdf")
        all_pages: list[ParsedPage] = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pn = page_num + 1

            # ── Extract tables ───────────────────────────────────────────
            table_bboxes: list[fitz.Rect] = []
            try:
                finder = page.find_tables()
                for table in finder.tables:
                    matrix = table.extract()
                    md = _matrix_to_markdown(matrix)
                    if md.strip():
                        all_pages.append(ParsedPage(page_number=pn, text=md, chunk_type="table"))
                    table_bboxes.append(fitz.Rect(table.bbox))
            except Exception as exc:
                logger.debug("Table extraction skipped on page %d: %s", pn, exc)

            # ── Extract text (skip blocks that overlap table areas) ───────
            text_parts: list[str] = []
            for block in page.get_text("blocks"):
                # block layout: (x0, y0, x1, y1, text, block_no, block_type)
                if block[6] != 0:  # skip image blocks
                    continue
                text = block[4].strip()
                if not text:
                    continue
                block_rect = fitz.Rect(block[:4])
                if any(block_rect.intersects(tb) for tb in table_bboxes):
                    continue  # text inside a table — already captured above
                text_parts.append(text)

            plain_text = "\n".join(text_parts).strip()
            if plain_text:
                all_pages.append(ParsedPage(page_number=pn, text=plain_text, chunk_type="text"))

        doc.close()

        if not all_pages:
            all_pages = [ParsedPage(page_number=1, text="", chunk_type="text")]

        return ParsedDocument(pages=all_pages, page_count=len(all_pages), mime_type="application/pdf")

import fitz  # PyMuPDF

from app.schemas import ParsedDocument, ParsedPage


class PDFParser:
    def parse(self, content: bytes) -> ParsedDocument:
        doc = fitz.open(stream=content, filetype="pdf")
        pages: list[ParsedPage] = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text("text").strip()
            if text:
                pages.append(ParsedPage(page_number=page_num + 1, text=text))

        doc.close()

        if not pages:
            pages = [ParsedPage(page_number=1, text="")]

        return ParsedDocument(
            pages=pages,
            page_count=len(pages),
            mime_type="application/pdf",
        )

import base64
import logging

from openai import OpenAI  # synchronous client — runs safely inside asyncio.to_thread

from app.config import settings
from app.schemas import ParsedDocument, ParsedPage

logger = logging.getLogger(__name__)

_VISION_MODEL = "gpt-4o"
_CAPTION_PROMPT = (
    "Describe this image in full detail. Include all visible text, numbers, labels, "
    "chart values, table contents, and any other data present. Be precise and thorough."
)
_MAX_TOKENS = 1024


class ImageParser:
    """Captions images using GPT-4o vision.

    Uses the synchronous OpenAI client so it can run inside asyncio.to_thread
    without spawning a nested event loop.
    """

    def __init__(self) -> None:
        self._client = OpenAI(api_key=settings.openai_api_key)

    def parse(self, content: bytes, mime_type: str = "image/jpeg") -> ParsedDocument:
        b64 = base64.b64encode(content).decode("utf-8")
        data_url = f"data:{mime_type};base64,{b64}"

        try:
            response = self._client.chat.completions.create(
                model=_VISION_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
                            {"type": "text", "text": _CAPTION_PROMPT},
                        ],
                    }
                ],
                max_tokens=_MAX_TOKENS,
            )
            caption = response.choices[0].message.content or ""
        except Exception as exc:
            logger.warning("GPT-4V captioning failed (%s), using empty caption", exc)
            caption = ""

        return ParsedDocument(
            pages=[ParsedPage(page_number=1, text=caption, chunk_type="image_caption")],
            page_count=1,
            mime_type=mime_type,
        )

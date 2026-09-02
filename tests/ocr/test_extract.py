import io

from PIL import Image, ImageDraw, ImageFont

from orub.domain.result import Err, Ok
from orub.ocr.errors import InvalidImage
from orub.ocr.extract import run_ocr


def _catno_image_bytes(text: str) -> bytes:
    image = Image.new("RGB", (400, 120), color="white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=60)
    draw.text((20, 20), text, fill="black", font=font)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def test_run_ocr_extracts_text_from_a_clear_image() -> None:
    match run_ocr(_catno_image_bytes("XL152")):
        case Ok(value=text):
            assert text.strip() == "XL152"
        case Err(error=error):
            raise AssertionError(f"expected Ok, got Err({error})")


def test_run_ocr_rejects_non_image_bytes() -> None:
    match run_ocr(b"not an image"):
        case Err(error=InvalidImage()):
            pass
        case other:
            raise AssertionError(f"expected Err(InvalidImage), got {other}")

"""Run the scanned-PDF OCR path offline with a deterministic mock provider."""

from __future__ import annotations

import argparse
import io
from pathlib import Path

from PIL import Image, ImageDraw

from file_processing import FileProcessingService


class MockOCRProvider:
    """Return predictable text while recording each rendered page request."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, int, str]] = []

    def extract_text(self, *, filename: str, content: bytes, mime_type: str) -> str:
        self.calls.append((filename, len(content), mime_type))
        return f"MOCK_OCR_PAGE_{len(self.calls)}"


def _make_sample_pages() -> list[Image.Image]:
    images = []
    for page_number in (1, 2):
        image = Image.new("RGB", (960, 540), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((48, 48, 912, 492), outline="#243b53", width=5)
        draw.text((88, 110), f"Offline sample slide {page_number}", fill="#102a43")
        draw.text((88, 180), "Raster-only page for the OCR fallback demo", fill="#486581")
        images.append(image)
    return images


def make_image_only_pdf(image_paths: list[Path]) -> bytes:
    images: list[Image.Image] = []
    try:
        if image_paths:
            for path in image_paths:
                with Image.open(path) as source:
                    images.append(source.convert("RGB"))
        else:
            images = _make_sample_pages()

        output = io.BytesIO()
        first, *remaining = images
        first.save(output, format="PDF", save_all=True, append_images=remaining)
        return output.getvalue()
    finally:
        for image in images:
            image.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Exercise scanned-PDF page rendering without calling Gemini."
    )
    parser.add_argument(
        "images",
        nargs="*",
        type=Path,
        help="Optional page images; defaults to generated raster-only sample pages.",
    )
    args = parser.parse_args()

    missing = [str(path) for path in args.images if not path.is_file()]
    if missing:
        parser.error("Image file(s) not found: " + ", ".join(missing))

    provider = MockOCRProvider()
    service = FileProcessingService(ocr_provider=provider)
    result = service.process(
        filename="offline-mock-slides.pdf",
        content=make_image_only_pdf(args.images),
        content_type="application/pdf",
    )

    print("Mode: offline mock (no Gemini API request)")
    print(f"Input pages: {len(args.images) or 2}")
    print(f"OCR fallback calls: {len(provider.calls)}")
    print(f"Metadata: {result.metadata}")
    print("Recognized text:")
    print(result.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Run one Gemini OCR request against a local image."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from file_processing import FileProcessingError, FileProcessingService


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the File Processing OCR demo.")
    parser.add_argument("image", type=Path, help="Path to a local PNG, JPG, or WEBP image")
    args = parser.parse_args()

    if not args.image.is_file():
        print(f"Không tìm thấy ảnh: {args.image}", file=sys.stderr)
        return 2

    try:
        result = FileProcessingService.from_env().process(
            filename=args.image.name,
            content=args.image.read_bytes(),
            content_type={".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(args.image.suffix.lower()),
        )
    except FileProcessingError as exc:
        print(json.dumps(exc.to_dict(), ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    print(result.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

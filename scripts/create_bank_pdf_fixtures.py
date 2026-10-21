"""Rebuild two self-authored PDF test fixtures; no private user material."""

import io
from pathlib import Path
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject


def main():
    root = Path(__file__).resolve().parents[1] / "fixtures"
    with Image.open(root / "question_bank_scan_demo.png") as image:
        scan = io.BytesIO()
        image.convert("RGB").save(scan, format="PDF", resolution=144)
    raw = scan.getvalue()
    (root / "question_bank_scan_demo.pdf").write_bytes(raw)
    writer = PdfWriter()
    writer.append(PdfReader(io.BytesIO(raw)))
    page = writer.add_blank_page(600, 600)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): writer._add_object(font)}
            )
        }
    )
    content = DecodedStreamObject()
    content.set_data(
        b"BT /F1 16 Tf 40 540 Td (3. Explain reliable transport protocols.) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(content)
    writer.write(root / "question_bank_mixed_demo.pdf")


if __name__ == "__main__":
    main()

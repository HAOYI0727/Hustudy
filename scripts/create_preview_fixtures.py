"""Generate self-authored Office fixtures; never reads user courses."""

from pathlib import Path
from docx import Document
from pptx import Presentation
from pptx.util import Inches
from pypdf import PdfWriter


def create_fixtures(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    word = Document()
    word.add_heading("Hustudy Office Preview", 0)
    word.add_paragraph("Self-authored DOCX first paragraph.")
    table = word.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Ordered table block"
    table.cell(0, 1).text = "Source stays docx_block"
    word.add_paragraph("Final paragraph after the table.")
    word.save(root / "preview_demo.docx")
    deck = Presentation()
    for index in (1, 2):
        slide = deck.slides.add_slide(deck.slide_layouts[6])
        if index == 2:
            slide._element.set(
                "show", "0"
            )  # Must still be exported to preserve slide/page identity.
        slide.shapes.add_textbox(
            Inches(1), Inches(1), Inches(8), Inches(2)
        ).text = f"Hustudy Preview Slide {index}"
        slide.shapes.add_textbox(
            Inches(1), Inches(3), Inches(8), Inches(1)
        ).text = "Self-authored fixture, no private course material."
    deck.save(root / "preview_demo.pptx")
    blank = PdfWriter()
    blank.add_blank_page(width=300, height=400)
    blank.write(root / "no_text_demo.pdf")


if __name__ == "__main__":
    create_fixtures(Path(__file__).resolve().parents[1] / "fixtures")

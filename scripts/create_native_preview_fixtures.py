"""Self-authored styled Office files for direct-format browser acceptance."""

from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt
from docx import Document
from docx.shared import Inches as WordInches
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE


def create(root):
    root.mkdir(exist_ok=True, parents=True)
    image = Image.new("RGB", (220, 100), "#2c609e")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 25, 80, 75), fill="#a1dcf5")
    draw.line((80, 50, 180, 50), fill="white", width=4)
    picture = BytesIO()
    image.save(picture, format="PNG")
    deck = Presentation()
    for index in (1, 2):
        slide = deck.slides.add_slide(deck.slide_layouts[6])
        if index == 2:
            slide._element.set("show", "0")
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = RGBColor.from_string("EAF0FA")
        box = slide.shapes.add_textbox(Inches(0.6), Inches(0.5), Inches(8), Inches(1))
        run = box.text_frame.paragraphs[0].add_run()
        run.text = f"Native PPTX Slide {index}"
        run.font.size = Pt(32)
        run.font.bold = True
        run.font.color.rgb = RGBColor.from_string("24538D")
        if index == 1:
            table = slide.shapes.add_table(
                2, 2, Inches(0.7), Inches(2), Inches(4), Inches(1.5)
            ).table
            table.cell(0, 0).text = "Protocol"
            table.cell(0, 1).text = "Window"
            table.cell(1, 0).text = "Synthetic"
            table.cell(1, 1).text = "42"
            slide.shapes.add_picture(
                BytesIO(picture.getvalue()), Inches(5.5), Inches(2.1), width=Inches(3)
            )
        else:
            slide.shapes.add_textbox(
                Inches(1), Inches(2), Inches(7), Inches(1)
            ).text = "Hidden slide kept in original order."
    deck.save(root / "native_preview.pptx")
    word = Document()
    word.add_heading("Native DOCX Page 1", 0)
    word.add_paragraph("Styled Word paragraph before the table.").runs[0].bold = True
    table = word.add_table(rows=2, cols=2)
    table.style = "Table Grid"
    table.cell(0, 0).text = "Ordered table"
    table.cell(0, 1).text = "Value"
    table.cell(1, 0).text = "Original document"
    table.cell(1, 1).text = "42"
    word.add_picture(BytesIO(picture.getvalue()), width=WordInches(2))
    paragraph = word.add_paragraph()
    relation = paragraph.part.relate_to(
        "https://preview.invalid/private-data",
        RELATIONSHIP_TYPE.HYPERLINK,
        is_external=True,
    )
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), relation)
    run = OxmlElement("w:r")
    text = OxmlElement("w:t")
    text.text = "External link stays inert"
    run.append(text)
    link.append(run)
    paragraph._p.append(link)
    word.add_page_break()
    word.add_heading("Native DOCX Page 2", 0)
    word.add_paragraph("Explicit page break and final paragraph.")
    word.add_paragraph("<script>window.previewInjected=true</script>")
    word.save(root / "native_preview.docx")


if __name__ == "__main__":
    create(Path(__file__).resolve().parents[1] / "fixtures")

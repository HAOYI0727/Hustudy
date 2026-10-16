"""Text in nested PowerPoint groups must remain readable/indexable (FR-04)."""

from pptx import Presentation
from pptx.util import Inches
from app.services.materials import parse_document


def test_nested_group_text_table_order_and_slide_locator(tmp_path):
    deck = Presentation()
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    slide.shapes.add_textbox(0, 0, Inches(3), Inches(1)).text = "组合前"
    group = slide.shapes.add_group_shape()
    group.shapes.add_textbox(0, 0, Inches(3), Inches(1)).text = "外层组合"
    nested = group.shapes.add_group_shape()
    nested.shapes.add_textbox(0, 0, Inches(3), Inches(1)).text = "嵌套核心知识"
    table_shape = slide.shapes.add_table(1, 2, 0, 0, Inches(4), Inches(1))
    table_shape.table.cell(0, 0).text = "有序表格"
    table_shape.table.cell(0, 1).text = "数值 42"
    # Moving an existing table into a group preserves its source tree order.
    nested.shapes._spTree.insert_element_before(table_shape._element, "p:extLst")
    slide.shapes.add_textbox(0, 0, Inches(3), Inches(1)).text = "组合后"
    empty = deck.slides.add_slide(deck.slide_layouts[6])
    assert len(empty.shapes) == 0
    last = deck.slides.add_slide(deck.slide_layouts[6])
    last.shapes.add_textbox(0, 0, Inches(3), Inches(1)).text = "第三页"
    path = tmp_path / "groups.pptx"
    deck.save(path)
    chunks = parse_document(path, ".pptx")
    assert [c["locator_value"] for c in chunks] == ["1", "3"]
    assert (
        chunks[0]["text"]
        == "组合前\n外层组合\n嵌套核心知识\n有序表格 | 数值 42\n组合后"
    )
    assert chunks[0]["end_offset"] == len(chunks[0]["text"])

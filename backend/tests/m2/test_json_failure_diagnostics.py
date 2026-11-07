"""Malformed responses stay rejected; diagnostics never copy model content."""

import pytest

from app.ai.providers import json_failure_message


@pytest.mark.parametrize(
    "content,expected",
    [
        ("", "最终内容为空"),
        ('```json\n{"secret":"private-source"}\n```', "代码围栏"),
        ('{"answer":"private-source\nnext"}', "未转义的换行"),
        ('{"answer":"private-source\\q"}', "非法转义"),
        ('{"answer":"private-source"} trailing', "额外内容"),
        ('{"answer":"private-source",}', "尾逗号"),
        ('{"answer":"private-source" "x":1}', "分隔符"),
        ('{"answer":"private-source', "语法不完整"),
    ],
)
def test_syntax_categories_are_fixed_and_do_not_echo_content(content, expected):
    message = json_failure_message(content)
    assert expected in message
    assert "private-source" not in message
    assert "未采纳结果" in message


def test_prompt_has_literal_json_escaping_and_bounded_complete_output_guidance():
    from app.ai.study_reports import REPORT_PROMPT

    assert "正文换行写为\\n" in REPORT_PROMPT
    assert '双引号写为\\"' in REPORT_PROMPT
    assert "反斜杠写为\\\\" in REPORT_PROMPT
    assert "不能为了压缩篇幅丢掉" in REPORT_PROMPT

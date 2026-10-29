"""Read explicitly labelled source values; never infer from arbitrary numbers."""

import re


def source_values(text, *, header=False):
    result = {}
    for key, labels, lower, upper, unit in (
        ("year", "题目年份|考试年份|年份", 1900, 2200, "年"),
        ("points", "分值|题目分值|本题分值", 1, 500, "分"),
    ):
        found = re.findall(
            rf"(?m)^\s*(?:\#{{1,6}}\s*)?(?:{labels})\s*[:：]\s*(\d+)\s*{unit}?\s*$",
            text,
        )
        values = {int(v) for v in found if lower <= int(v) <= upper}
        if len(values) == 1:
            result[key] = values.pop()
    if header and "year" not in result:
        years = re.findall(
            r"(?m)^\s*(?:\#{1,6}\s*)?(\d{4})年[^\n]{0,80}(?:试卷|考试|真题)", text
        )
        values = {int(v) for v in years if 1900 <= int(v) <= 2200}
        if len(values) == 1:
            result["year"] = values.pop()
    return result

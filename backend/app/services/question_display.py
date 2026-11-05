"""Explicit source numbers define display groups; no inferred question merging."""

import re
import unicodedata

NUMERALS = "零〇一二三四五六七八九十百千两"


def integer(token):
    if token.isdecimal():
        return int(token)
    digits = {c: i for i, c in enumerate("零一二三四五六七八九")}
    digits.update({"〇": 0, "两": 2})
    value, current = 0, 0
    for char in token:
        if char in digits:
            current = digits[char]
        else:
            value += (current or 1) * {"十": 10, "百": 100, "千": 1000}[char]
            current = 0
    return value + current


def display_group(number, paper_id):
    raw = unicodedata.normalize("NFKC", str(number)).strip()
    if not re.fullmatch(rf"[第题大\s\d{NUMERALS}.、:()\-/]+", raw):
        return None
    tokens = re.findall(rf"\d+|[{NUMERALS}]+", raw)
    if not tokens:
        return None
    order = [integer(token) for token in tokens]
    return {
        "key": f"{paper_id}:{order[0]}",
        "label": f"第{order[0]}大题",
        "order": order,
    }


def order_rows(rows):
    papers = {
        pid: index for index, pid in enumerate(dict.fromkeys(q.paper_id for q in rows))
    }
    ordered = []
    for index, row in enumerate(rows):
        group = display_group(row.number, row.paper_id)
        ordered.append(
            (
                (
                    papers[row.paper_id],
                    0 if group else 1,
                    group["order"] if group else [index],
                ),
                row,
            )
        )
    return [row for _, row in sorted(ordered, key=lambda pair: pair[0])]


def has_major_groups(rows):
    seen = set()
    for row in rows:
        group = display_group(row.number, row.paper_id)
        if not group:
            continue
        if len(group["order"]) > 1 or group["key"] in seen:
            return True
        seen.add(group["key"])
    return False

"""Lossless, bounded conversion of explicit tables to stored GFM source."""

import re
from html.parser import HTMLParser


def table(headers, rows):
    width = len(headers) or (len(rows[0]) if rows else 0)
    if not 1 <= width <= 32 or len(rows) > 200 or any(len(r) != width for r in rows):
        raise ValueError("表格列数不一致或超过32列/200行，请核对原表")

    def cell(text):
        # Backslash-escaped pipes keep math/logic in one GFM cell.
        text = str(text).replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"(?<!\\)\|", r"\|", text)
        return text.replace("\n", " ").strip()

    def row(values):
        return "| " + " | ".join(cell(v) for v in values) + " |"

    return "\n".join(
        [row(headers or [""] * width), row(["---"] * width), *(row(r) for r in rows)]
    )


class SimpleTable(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.current, self.parts = [], None, None
        self.invalid = False
        self.header = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.current = []
        elif tag in {"td", "th"}:
            self.parts = []
            self.header |= tag == "th" and not self.rows
            if any(k in {"rowspan", "colspan"} and v != "1" for k, v in attrs):
                self.invalid = True
        elif tag == "br" and self.parts is not None:
            self.parts.append(" ")
        elif tag not in {
            "table",
            "thead",
            "tbody",
            "tfoot",
            "b",
            "strong",
            "em",
            "i",
            "sub",
            "sup",
            "span",
        }:
            self.invalid = True
        if tag in {"sub", "sup"} and self.parts is not None:
            self.invalid = True

    def handle_data(self, data):
        if self.parts is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.current is not None and self.parts is not None:
            self.current.append("".join(self.parts))
            self.parts = None
        elif tag == "tr" and self.current is not None:
            self.rows.append(self.current)
            self.current = None


def normalize(text):
    if not text:
        return text
    # Keep code and display math literal, including tabs/pipes inside them.
    protected = re.split(r"(```[\s\S]*?```|~~~[\s\S]*?~~~|\$\$[\s\S]*?\$\$)", text)
    for i in range(0, len(protected), 2):
        value = protected[i]

        def convert_html(match):
            parser = SimpleTable()
            parser.feed(match[0])
            if parser.invalid or not parser.rows:
                return "\n```html\n" + match[0] + "\n```\n"
            try:
                return (
                    "\n"
                    + table(
                        parser.rows[0] if parser.header else [],
                        parser.rows[1:] if parser.header else parser.rows,
                    )
                    + "\n"
                )
            except ValueError:
                return "\n```html\n" + match[0] + "\n```\n"

        value = re.sub(
            r"<table\b[^>]*>[\s\S]*?</table\s*>", convert_html, value, flags=re.I
        )
        lines, result, n = value.split("\n"), [], 0
        while n < len(lines):
            delimiter = (
                "\t"
                if "\t" in lines[n]
                else " | "
                if " | " in lines[n] and not lines[n].lstrip().startswith("|")
                else None
            )
            if (
                delimiter
                and lines[n].strip()
                and not lines[n].startswith(("    ", "\t"))
            ):
                end = n
                while (
                    end < len(lines) and delimiter in lines[end] and lines[end].strip()
                ):
                    end += 1
                rows = [line.split(delimiter) for line in lines[n:end]]
                balanced = all(cell.count("$") % 2 == 0 for row in rows for cell in row)
                if (
                    len(rows) >= 2
                    and balanced
                    and all(len(r) == len(rows[0]) for r in rows)
                ):
                    try:
                        result.extend(["", table(rows[0], rows[1:]), ""])
                        n = end
                        continue
                    except ValueError:
                        pass
            result.append(lines[n])
            n += 1
        protected[i] = "\n".join(result)
    return "".join(protected).strip()

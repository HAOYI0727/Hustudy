"""Explicit Markdown boundaries; never infer question starts from prose."""

import re
import json
import shutil
import subprocess
from pathlib import Path
from fastapi import HTTPException

HEADER = "# Hustudy 题库 v1"
FIELDS = {
    "题型",
    "公共条件",
    "题干",
    "选项",
    "参考答案",
    "解析",
    "知识标签",
    "分值",
    "年份",
}


def fail(line, message):
    raise HTTPException(422, f"Markdown第{line}行：{message}")


def validate_file(name, raw):
    if not name.lower().endswith((".md", ".markdown")):
        raise HTTPException(422, "本地录入仅支持Markdown文件；其他格式请选择AI识别")
    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(413, "单份本地Markdown最多2MiB")
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        raise HTTPException(422, "Markdown必须使用UTF-8编码") from None
    parse(text)
    return text


def check_markup(text, line):
    # Code fences are handled by the scanner; disallow active/raw HTML and external images.
    if re.search(r"</?[A-Za-z][A-Za-z0-9:-]*(?:\s[^<>]*)?/?>|!\[", text):
        fail(line, "不支持HTML或外部图片，请使用Markdown表格及数学公式")
    without_code = re.sub(r"(`{3,}|~{3,})[^\n]*\n[\s\S]*?\1", "", text)
    without_code = re.sub(r"`[^`\n]*`", "", without_code)
    current = None
    expressions = []
    for mark in re.finditer(r"(?<!\\)\$\$|(?<!\\)\$", without_code):
        if current is None:
            current = mark
        elif current[0] == mark[0]:
            value = without_code[current.end() : mark.start()]
            if mark[0] == "$" and "\n" in value:
                fail(line, "行内公式不能跨行，请使用独立公式")
            expressions.append((value, ""))
            current = None
        else:
            fail(line, "行内与独立公式边界混用")
    if current:
        fail(line, "公式分隔符未闭合")
    for expression in expressions:
        depth = 0
        for match in re.finditer(r"(?<!\\)[{}]", "".join(expression)):
            depth += 1 if match[0] == "{" else -1
            if depth < 0:
                fail(line, "公式花括号不匹配")
        if depth:
            fail(line, "公式花括号不匹配")
    lines = without_code.splitlines()
    n = 0
    while n < len(lines):
        if lines[n].lstrip().startswith("|"):
            group = []
            while n < len(lines) and lines[n].lstrip().startswith("|"):
                value = lines[n].strip()
                if not value.endswith("|"):
                    fail(line + n, "表格每行须以竖线开始和结束")
                group.append(re.split(r"(?<!\\)\|", value)[1:-1])
                n += 1
            if len(group) < 2 or not all(
                re.fullmatch(r"\s*:?-{3,}:?\s*", c) for c in group[1]
            ):
                fail(line + n - len(group), "表格缺少合法分隔行")
            if any(len(row) != len(group[0]) for row in group):
                fail(line + n - len(group), "表格列数不一致；单元格内竖线须转义")
        else:
            n += 1

    return ["".join(expression) for expression in expressions]


def parse(text):
    if len(text) > 240000 or "\x00" in text:
        fail(1, "正文超过24万字符或含非法空字符")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip().lstrip("\ufeff") != HEADER:
        fail(1, f"首行必须为 {HEADER}")
    questions, seen, item, field, fence, math = [], set(), None, None, None, False
    offset = len(lines[0])
    for number, raw in enumerate(lines[1:], 2):
        value = raw.rstrip("\r\n")
        stripped = value.strip()
        marker = re.match(r"^\s*(`{3,}|~{3,})", value)
        protected = fence is not None or math
        if not protected and stripped.startswith("## 题目 "):
            identity = stripped.removeprefix("## 题目 ").strip()
            if (
                not re.fullmatch(r"[1-9]\d{0,3}(?:-[1-9]\d{0,3})?", identity)
                or identity in seen
            ):
                fail(number, "题号须为唯一数字或大题-子题，如1-1")
            if item:
                item["end"] = offset
                questions.append(item)
            seen.add(identity)
            item = dict(
                number=identity, start=offset, end=len(text), fields={}, line=number
            )
            field = None
        elif not protected and stripped.startswith("### "):
            key = stripped[4:]
            if item is None or key not in FIELDS:
                fail(number, "未知字段或字段不属于任何题目")
            if key in item["fields"]:
                fail(number, "字段重复：" + key)
            item["fields"][key] = [number + 1, ""]
            field = key
        elif not protected and stripped.startswith(("# ", "## ")):
            fail(number, "未知结构标题；正文小标题请使用四级及以下标题")
        elif item is not None and field:
            item["fields"][field][1] += raw
        elif stripped:
            fail(number, "正文未归属到题目字段")
        if marker:
            if fence is None:
                fence = marker[1]
            elif marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                fence = None
        if fence is None and stripped == "$$":
            math = not math
        offset += len(raw)
    if fence or math:
        fail(len(lines), "代码块或独立公式未闭合")
    if item:
        questions.append(item)
    if not 1 <= len(questions) <= 1000:
        fail(1, "每份Markdown必须包含1至1000题")
    result, math_values, math_lines = [], [], []
    for item in questions:
        fields = item["fields"]
        for key in ("题型", "题干"):
            if key not in fields or not fields[key][1].strip():
                fail(item["line"], "缺少非空字段：" + key)
        values = {key: value.strip() for key, (_, value) in fields.items()}
        for key, (number, value) in fields.items():
            formulas = check_markup(value, number)
            math_values.extend(formulas)
            math_lines.extend([number] * len(formulas))
        kind = {"选择题": "single_choice", "解答题": "solution"}.get(values["题型"])
        if not kind:
            fail(fields["题型"][0], "题型只能为选择题或解答题")
        options = []
        if kind == "single_choice":
            matches = list(re.finditer(r"(?m)^([A-D])\. ", values.get("选项", "")))
            if [m[1] for m in matches] != list("ABCD") or (
                matches and matches[0].start()
            ):
                fail(item["line"], "选择题选项必须独立以A. 至D. 开头")
            options = [
                values["选项"][
                    m.end() : matches[i + 1].start() if i < 3 else len(values["选项"])
                ].strip()
                for i, m in enumerate(matches)
            ]
            if any(not o or len(o) > 10000 for o in options) or len(set(options)) != 4:
                fail(item["line"], "四个选项须非空、不同且不超过10000字符")
        elif values.get("选项"):
            fail(item["line"], "解答题不能包含选项字段")
        answer = values.get("参考答案") or None
        if kind == "single_choice" and answer and answer not in "ABCD":
            fail(item["line"], "选择题参考答案只能为A/B/C/D，未知请留空")
        if kind == "single_choice" and answer and len(answer) != 1:
            fail(item["line"], "单选题只能有一个答案")
        stem = (values.get("公共条件", "") + "\n\n" + values["题干"]).strip()
        if len(stem) > 20000:
            fail(item["line"], "题干与公共条件总计不能超过20000字符")
        points = values.get("分值", "")
        if points and (not points.isdigit() or not 1 <= int(points) <= 500):
            fail(item["line"], "分值须为空或1至500的整数")
        year = values.get("年份", "")
        if year and (not year.isdigit() or not 1900 <= int(year) <= 2200):
            fail(item["line"], "年份须为空或1900至2200的整数")
        tags = [
            t.strip()
            for t in re.split(r"[,，、;；]", values.get("知识标签", ""))
            if t.strip()
        ]
        if len(set(tags)) > 5 or any(len(t) > 240 for t in tags):
            fail(item["line"], "最多5个知识标签，每个最多240字符")
        result.append(
            dict(
                number=item["number"],
                stem=stem,
                kind=kind,
                answer=answer,
                options=options,
                blank_answers=[],
                unique_answer=None,
                tag_names=list(dict.fromkeys(tags)),
                points=int(points) if points else None,
                **({"year": int(year) if year else None} if "年份" in fields else {}),
                explanation=values.get("解析", ""),
                start=item["start"],
                end=item["end"],
                content_profile="with_answers" if answer else "questions_only",
                warnings=[] if answer else ["未提供参考答案，请核对后自行批改"],
                strict_markdown=True,
            )
        )
    if math_values:
        if len(math_values) > 1000 or sum(map(len, math_values)) > 100000:
            fail(1, "公式数量或长度超过校验预算")
        node = shutil.which("node")
        script = Path(__file__).resolve().parents[3] / "scripts/validate_bank_math.mjs"
        if not node:
            fail(1, "服务端缺少Node公式校验运行时，请配置后重试")
        try:
            checked = subprocess.run(
                [node, str(script)],
                input=json.dumps(math_values),
                capture_output=True,
                text=True,
                timeout=15,
                check=True,
            )
            invalid = json.loads(checked.stdout)
        except (OSError, ValueError, subprocess.SubprocessError):
            fail(1, "公式校验组件不可用，请检查本地前端依赖与Node运行时")
        if invalid:
            fail(
                math_lines[invalid[0]],
                "公式不受当前KaTeX支持或语法错误，请修正后重新导入",
            )
    return result

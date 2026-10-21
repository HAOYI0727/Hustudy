"""Conservative question/answer/explanation separation, without model inference."""

import re
from fastapi import HTTPException

START = re.compile(r"(?m)^\s*(?:第\s*)?(\d{1,4})\s*(?:[.、．)）]|题[：:、.]?)\s*")
OPTION = re.compile(r"(?:^|[ \t]+)([A-DＡ-Ｄ])[.．、:：)）]\s*", re.M)
GROUP = re.compile(
    r"(?m)^[ \t]*(?:#{1,6}[ \t]*)?(?:题目|大题)[ \t]*(\d{1,3})[ \t]*(?:[:：][^\n]*)?[ \t]*$"
)
META = re.compile(
    r"^\s*(?:【\s*|\[\s*)?(参考答案|正确答案|答案解析|答案|解析|详解|解答|分析|知识点|知识标签|标签|唯一答案|分值)(?:\s*[】\]]\s*[:：]?|\s*[:：]|\s*$)\s*(.*)$"
)
ANSWER_SECTION = re.compile(
    r"(?m)^\s*(?:#{1,6}\s*)?(?:【|\[)?(?:参考答案与解析|答案与解析|参考答案及解析|答案及解析|参考答案|答案汇总)(?:】|\])?\s*[:：]?\s*$"
)


def parse(content):
    from .question_bank import normal

    if not content.strip():
        raise HTTPException(422, "没有可识别文字，请核对图片或补录题目")
    # Separate an explicit answer appendix before splitting numbered questions.
    appendix = {}
    section = ANSWER_SECTION.search(content)
    if section and not START.search(content[section.end() :]):
        section = None
    body = content[: section.start()] if section else content
    if section:
        tail = content[section.end() :]
        starts = list(START.finditer(tail))
        for i, m in enumerate(starts):
            appendix[m[1]] = tail[
                m.end() : starts[i + 1].start() if i + 1 < len(starts) else len(tail)
            ].strip()
    starts = list(START.finditer(body))
    groups = list(GROUP.finditer(body))
    spans = [
        (
            m[1],
            m.end(),
            min(
                starts[i + 1].start() if i + 1 < len(starts) else len(body),
                next((g.start() for g in groups if g.start() >= m.end()), len(body)),
            ),
        )
        for i, m in enumerate(starts)
    ] or [("1", 0, len(body))]
    if len(spans) > 1000:
        raise HTTPException(422, "单次最多识别1000题，请分卷上传")
    result = []
    for number, start, end in spans:
        raw = body[start:end]
        # Common rich-text labels may share a line; retain literal math/code otherwise.
        raw = re.sub(
            r"(?<!^)\s*(?=【(?:答案|正确答案|参考答案|解析|分析|解答|知识点|知识标签)】)",
            "\n",
            raw,
        )
        lines, values, field = [], {}, None
        for line in raw.splitlines():
            match = META.match(line)
            if match:
                field = {
                    "分析": "解析",
                    "解答": "解析",
                    "答案解析": "解析",
                    "详解": "解析",
                }.get(match[1], match[1])
                values[field] = (values.get(field, "") + "\n" + match[2]).strip()
            elif field:
                values[field] += "\n" + line
            else:
                lines.append(line)
        text = "\n".join(lines).strip()
        warnings = []
        group = next((g[1] for g in reversed(groups) if g.end() <= start), None)
        # Grouped worked-solution sheets often omit '答案：'. Keep provided prose
        # separate after an explicit terminal question/directive line. Never infer
        # a choice key or fabricate an answer from the subject matter.
        implicit_answer = None
        if group and not values and not OPTION.search(text):
            question_lines = text.splitlines()
            for index, line in enumerate(question_lines[:6]):
                if re.search(r"[？?。]\s*$", line) and index + 1 < len(question_lines):
                    tail = "\n".join(question_lines[index + 1 :]).strip()
                    if len(tail) >= 4:
                        text = "\n".join(question_lines[: index + 1]).strip()
                        implicit_answer = tail
                        warnings.append(
                            "按分组题号及问句/指令终止行分离了无标签参考解答，请对照原文核对"
                        )
                    break
        if re.search(r"!\[.*?\]\(|!\[\[asset:", text):
            warnings.append(
                "正文含图片引用，请在插图区上传或关联实际图片，核对后再确认"
            )
            text = re.sub(
                r"!\[[^\]]*\]\([^)]*\)|!\[\[asset:[^\]]*\]\]", "[插图待关联]", text
            )
        marks = list(OPTION.finditer(text))
        options = []
        if marks:
            stem = text[: marks[0].start()].strip()
            if [normal(m[1]) for m in marks] == list("ABCD"):
                options = [
                    text[
                        m.end() : marks[i + 1].start() if i + 1 < 4 else len(text)
                    ].strip()
                    for i, m in enumerate(marks)
                ]
            kind = "single_choice"
        else:
            stem = text
            kind = "single_choice" if re.search(r"单选|选择题", text) else "solution"
        answer = next(
            (
                values[k].strip()
                for k in ("正确答案", "答案", "参考答案")
                if values.get(k, "").strip()
            ),
            None,
        )
        answer = answer or implicit_answer
        explanation = values.get("解析", "").strip()
        if number in appendix:
            tail = appendix[number]
            m = re.match(
                r"(?:【?(?:答案|正确答案|参考答案)】?[:：]?\s*)?([A-DＡ-Ｄ])(?:\s|[.。；;]|$)",
                tail,
            )
            if kind == "single_choice" and m and not answer:
                answer = normal(m[1])
                explanation = explanation or tail[m.end() :].strip()
            elif not answer:
                warnings.append("检测到独立答案段，请人工核对后填写逐题答案")
                explanation = explanation or tail
        # Only an explicit concluding choice is extracted, never infer from prose.
        if kind == "single_choice" and not answer and explanation:
            m = re.search(
                r"(?:故选|应选|正确选项(?:为|是)?|答案(?:为|是|[:：]))\s*([A-DＡ-Ｄ])(?=[。．.，,；;\s]|$)",
                explanation,
            )
            if m:
                answer = normal(m[1])
        if kind == "single_choice" and answer:
            candidate = normal(answer).upper()
            m = re.fullmatch(r"([A-D])(?:[。．.]|\s.*)?", candidate, re.S)
            if m:
                answer = m[1]
        profile = (
            "answer_only"
            if not text
            else "with_explanations"
            if explanation
            else "with_answers"
            if answer
            else "questions_only"
        )
        if not answer and kind != "solution":
            warnings.append("只有题目或解析未明确答案，请补充答案；不会猜测正确结果")
        if profile == "answer_only":
            warnings.append("此段缺少题干，可能是独立答案或解析")
        tags = re.split(
            r"[,，、;；]",
            next(
                (values[k] for k in ("知识点", "知识标签", "标签") if k in values), ""
            ),
        )
        points = values.get("分值", "").strip().removesuffix("分")
        result.append(
            dict(
                number=f"{group}-{number}" if group else number,
                stem=stem or "待补充题干（仅答案或解析）",
                kind=kind,
                answer=answer,
                options=options,
                blank_answers=[a.strip() for a in answer.split("||")]
                if kind == "fill_blank" and answer
                else [],
                unique_answer=None,
                tag_names=list(dict.fromkeys(t.strip() for t in tags if t.strip())),
                points=int(points)
                if points.isdigit() and 0 < int(points) <= 500
                else None,
                explanation=explanation,
                start=start,
                end=end,
                content_profile=profile,
                warnings=warnings,
            )
        )
    return result

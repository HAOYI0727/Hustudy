"""M4 snapshot/restore boundary preserves paper and attempt snapshots."""

from ..core import backup_contract as contract
import json
import hashlib
from ..models import (
    Topic,
    ExamAnalysisReport,
    PastPaper,
    PastQuestion,
    ExamBlueprint,
    ExamPaper,
    ExamAttempt,
    Mistake,
    ReviewTask,
    Feedback,
)

MODELS = [
    Topic,
    ExamAnalysisReport,
    PastPaper,
    PastQuestion,
    ExamBlueprint,
    ExamPaper,
    ExamAttempt,
    Mistake,
    ReviewTask,
    Feedback,
]


def snapshot(db, user_id):
    return contract.serialize(db, user_id, MODELS), []


def empty(db, user_id):
    contract.assert_empty(db, user_id, MODELS)


def validate(db, user_id, source_user, tables, all_ids, paths):
    decoded = contract.validate(
        db, user_id, source_user, MODELS, tables, all_ids, paths
    )
    papers = {row["id"]: row for row in tables["past_papers"]}
    topics = {row["id"]: row for row in tables["topics"]}
    versions = {row["id"]: row for row in tables["document_versions"]}
    documents = {row["id"]: row for row in tables["documents"]}
    chunks = {row["id"]: row for row in tables["document_chunks"]}
    for t in decoded["topics"]:
        merged = t["merged_into_id"]
        visited = {t["id"]}
        while merged:
            if (
                merged not in topics
                or merged in visited
                or topics[merged]["course_id"] != t["course_id"]
            ):
                raise ValueError("知识标签重定向越界或循环")
            visited.add(merged)
            merged = topics[merged]["merged_into_id"]
    from .topic_tree import validate_links

    for item in decoded["topics"]:
        metadata = json.loads(item["sources_json"])
        if (
            "deleted_by_user" in metadata
            and type(metadata["deleted_by_user"]) is not bool
        ):
            raise ValueError("标签删除状态必须为布尔值")
        hierarchy = metadata.get("hierarchy", {})
        if not isinstance(hierarchy, dict) or set(hierarchy) - {"parent_id"}:
            raise ValueError("标签层级元数据格式不合法")

    for course_id in {t["course_id"] for t in decoded["topics"]}:
        validate_links(
            {
                t["id"]: json.loads(t["sources_json"])
                .get("hierarchy", {})
                .get("parent_id")
                for t in decoded["topics"]
                if t["course_id"] == course_id and not t["merged_into_id"]
            }
        )
    assets = {row["id"]: row for row in tables["assets"]}
    jobs = {row["id"]: row for row in tables["processing_jobs"]}

    def check_images(images, course_id, limit=8):
        import math

        if not isinstance(images, list) or len(images) > limit:
            raise ValueError("题库图片集合超过预算")
        for image in images:
            asset = (
                assets.get(image.get("asset_id")) if isinstance(image, dict) else None
            )
            box = image.get("box", [0, 0, 1, 1]) if asset else None
            if not asset or asset["course_id"] != course_id:
                raise ValueError("题库图片引用越界")
            if (
                not isinstance(box, list)
                or len(box) != 4
                or any(type(n) not in (float, int) or not math.isfinite(n) for n in box)
            ):
                raise ValueError("题库图片裁剪结构不正确")
            x, y, w, h = box
            if (
                x < 0
                or y < 0
                or w <= 0
                or h <= 0
                or x + w > 1.000001
                or y + h > 1.000001
            ):
                raise ValueError("题库图片裁剪越界")

    for paper in decoded["past_papers"]:
        meta = json.loads(paper["bank_meta_json"])
        if not isinstance(meta, dict):
            raise ValueError("题库来源元数据必须为对象")
        from .bank_identity import validate as validate_identity

        validate_identity(meta.get("exam_identity"))
        extraction = meta.get("ai_extract")
        classification = meta.get("ai_topic_index")
        if classification:
            job = jobs.get(classification.get("job_id"))
            if classification.get("job_id") and (
                not job
                or job["type"] != "BANK_EXTRACT"
                or job["resource_id"] != paper["id"]
            ):
                raise ValueError("AI知识点任务引用不一致")
            if not isinstance(classification.get("input"), dict):
                raise ValueError("AI知识点预览结构不正确")
            for question in classification["input"]["questions"]:
                source = next(
                    (
                        q
                        for q in tables["past_questions"]
                        if q["id"] == question.get("question_id")
                    ),
                    None,
                )
                if not source or source["paper_id"] != paper["id"]:
                    raise ValueError("AI知识点题目引用越界")
            for tag in classification["input"]["topics"]:
                if (
                    tag["id"] not in topics
                    or topics[tag["id"]]["course_id"] != paper["course_id"]
                ):
                    raise ValueError("AI知识点词表引用越界")
        if extraction:
            job = (
                jobs.get(extraction.get("job_id")) if extraction.get("job_id") else None
            )
            if extraction.get("job_id") and (
                not job
                or job["type"] != "BANK_EXTRACT"
                or job["resource_id"] != paper["id"]
            ):
                raise ValueError("AI识别任务引用不一致")
            for source in extraction["sources"]:
                chunk = next(
                    (
                        c
                        for c in tables["document_chunks"]
                        if c["id"] == source.get("source_id")
                    ),
                    None,
                )
                if (
                    not chunk
                    or chunk["version_id"] != source.get("version_id")
                    or source["version_id"] != meta.get("version_id")
                ):
                    raise ValueError("AI识别原文引用不一致")
                if (
                    documents[versions[source["version_id"]]["document_id"]][
                        "course_id"
                    ]
                    != paper["course_id"]
                    or source["text"] not in chunk["text"]
                ):
                    raise ValueError("AI识别原文或课程不一致")
        image_job_id = meta.get("image_job_id")
        pdf_import = meta.get("pdf_import")
        if pdf_import:
            version = versions.get(pdf_import.get("version_id"))
            if (
                not version
                or documents[version["document_id"]]["course_id"] != paper["course_id"]
                or pdf_import.get("source_hash") != version["sha256"]
            ):
                raise ValueError("PDF识别来源引用不一致")
        if image_job_id:
            job = jobs.get(image_job_id)
            if (
                not job
                or job["type"] != "BANK_OCR"
                or job["resource_id"] != paper["id"]
            ):
                raise ValueError("图片识别任务引用不一致")
            check_images(
                [{"asset_id": aid} for aid in meta["image_import"]["asset_ids"]],
                paper["course_id"],
                20,
            )
        if "vision_checkpoints" in meta:
            from .bank_vision import Page

            pages = meta["vision_checkpoints"]
            ids = meta.get("image_import", {}).get("asset_ids", [])
            if not isinstance(pages, list) or len(pages) > len(ids) or len(pages) > 20:
                raise ValueError("AI转写页检查点数量不正确")
            for index, page in enumerate(pages):
                if not isinstance(page, dict) or page.get("asset_id") != ids[index]:
                    raise ValueError("AI转写页与原图顺序不一致")
                result = Page.model_validate(page.get("result"))
                if meta["image_import"].get("questions_only", True) and any(
                    b.answer is not None or b.explanation for b in result.blocks
                ):
                    raise ValueError("仅题目AI检查点包含答案")
        target = meta.get("duplicate_of")
        visited = {paper["id"]}
        while target:
            if (
                target not in papers
                or target in visited
                or papers[target]["course_id"] != paper["course_id"]
            ):
                raise ValueError("重复样本代表卷越界或循环")
            visited.add(target)
            target = json.loads(papers[target]["bank_meta_json"]).get("duplicate_of")
        version_id = meta.get("version_id")
        if version_id and (
            version_id not in versions
            or documents[versions[version_id]["document_id"]]["course_id"]
            != paper["course_id"]
        ):
            raise ValueError("题库原卷版本归属或课程不一致")

    def check_source(citation, course_id):
        chunk = chunks.get(citation.get("chunk_id"))
        version = versions.get(citation.get("version_id"))
        if not chunk or not version or chunk["version_id"] != version["id"]:
            raise ValueError("题库备份来源不一致")
        document = documents[version["document_id"]]
        quote = citation.get("quote")
        if (
            document["course_id"] != course_id
            or not isinstance(quote, str)
            or hashlib.sha256(quote.encode()).hexdigest() != citation.get("quote_hash")
            or chunk["text"]
            and quote not in chunk["text"]
            or citation.get("locator")
            != {"type": chunk["locator_type"], "value": chunk["locator_value"]}
        ):
            raise ValueError("题库备份引用的课程、摘录或定位不一致")

    for t in decoded["topics"]:
        for citation in json.loads(t["sources_json"]).get("citations", []):
            check_source(citation, t["course_id"])

    def check_pdf_version(data, course_id):
        vid = data.get("source_version_id")
        if vid and (
            vid not in versions
            or documents[versions[vid]["document_id"]]["course_id"] != course_id
        ):
            raise ValueError("题库PDF来源版本越界")
        context = data.get("context_stem", "")
        sources = data.get("context_sources", [])
        if (
            not isinstance(context, str)
            or len(context) > 50000
            or not isinstance(sources, list)
            or len(sources) > 200
        ):
            raise ValueError("大题上下文结构或预算不正确")
        check_images(data.get("context_illustrations", []), course_id, 40)
        whole = data.get("whole_stem", "")
        if not isinstance(whole, str) or len(whole) > 50000:
            raise ValueError("完整大题题干不正确或超过预算")
        check_images(data.get("whole_illustrations", []), course_id, 40)
        for source in sources:
            if not isinstance(source, dict) or set(source) - {
                "source_version_id",
                "citations",
            }:
                raise ValueError("大题上下文来源结构不正确")
            source_vid = source.get("source_version_id")
            if source_vid and (
                source_vid not in versions
                or documents[versions[source_vid]["document_id"]]["course_id"]
                != course_id
            ):
                raise ValueError("大题上下文来源版本越界")
            for citation in source.get("citations", []):
                check_source(citation, course_id)

    for question in decoded["past_questions"]:
        data = json.loads(question["bank_data_json"])
        if not isinstance(data, dict):
            raise ValueError("题库数据必须为对象")
        if not data:
            continue
        course_id = papers[question["paper_id"]]["course_id"]
        check_pdf_version(data, course_id)
        check_images(data.get("source_images", []), course_id, 40)
        check_images(data.get("illustrations", []), course_id)
        for topic_id in data.get("topic_ids", []):
            if topic_id not in topics or topics[topic_id]["course_id"] != course_id:
                raise ValueError("题库备份知识标签越界")
        for citation in data.get("citations", []):
            check_source(citation, course_id)
    exam_papers = {row["id"]: row for row in decoded["exam_papers"]}
    for ep in exam_papers.values():
        for question in json.loads(ep["questions_json"]):
            check_pdf_version(question, ep["course_id"])
            check_images(question.get("illustrations", []), ep["course_id"])
    for attempt in decoded["exam_attempts"]:
        snapshot = json.loads(attempt["snapshot_json"])
        grading = json.loads(attempt["grading_json"])
        if not isinstance(snapshot, dict) or not isinstance(grading, dict):
            raise ValueError("作答快照结构不正确")
        if snapshot:
            if (
                not isinstance(snapshot.get("questions"), list)
                or type(snapshot.get("duration_minutes")) is not int
                or not 1 <= snapshot["duration_minutes"] <= 180
            ):
                raise ValueError("作答快照题目或时长不正确")
            for q in snapshot["questions"]:
                check_pdf_version(q, exam_papers[attempt["paper_id"]]["course_id"])
                check_images(
                    q.get("illustrations", []),
                    exam_papers[attempt["paper_id"]]["course_id"],
                )
                for citation in q.get("citations", []):
                    check_source(
                        citation, exam_papers[attempt["paper_id"]]["course_id"]
                    )

    attempts_by_id = {a["id"]: a for a in decoded["exam_attempts"]}
    for mistake in decoded["mistakes"]:
        detail = json.loads(mistake["detail_json"])
        if (
            "removed_from_bank" in detail
            and type(detail["removed_from_bank"]) is not bool
        ):
            raise ValueError("错题移出状态不正确")
        redos = detail.get("redoes", {})
        if not isinstance(redos, dict):
            raise ValueError("错题重做记录结构不正确")
        course = exam_papers[attempts_by_id[mistake["attempt_id"]]["paper_id"]][
            "course_id"
        ]
        check_pdf_version(detail.get("question", {}), course)
        from datetime import datetime

        relapses = detail.get("relapses", {})
        if not isinstance(relapses, dict):
            raise ValueError("错题再次答错事件不正确")
        for event_id, event in relapses.items():
            if not isinstance(event, dict):
                raise ValueError("错题再次答错事件不正确")
            attempt = attempts_by_id.get(event.get("attempt_id"))
            if (
                not attempt
                or event_id != f"{attempt['id']}:{event.get('question_id')}"
                or exam_papers[attempt["paper_id"]]["course_id"] != course
                or type(event.get("sequence")) is not int
                or event["sequence"] < 1
                or not datetime.fromisoformat(event.get("completed_at", "")).tzinfo
            ):
                raise ValueError("错题再次答错来源或时间不正确")
            snapshot = json.loads(attempt["snapshot_json"])
            questions = snapshot.get("questions") or json.loads(
                exam_papers[attempt["paper_id"]]["questions_json"]
            )
            if not any(q.get("id") == event.get("question_id") for q in questions):
                raise ValueError("再次答错的题目不属于作答快照")
        for rid, item in redos.items():
            if (
                not isinstance(item, dict)
                or item.get("id") != rid
                or item.get("status")
                not in {"IN_PROGRESS", "NEEDS_SELF_REVIEW", "COMPLETED"}
            ):
                raise ValueError("错题重做状态不正确")
            question = item.get("question")
            if "sequence" in item and (
                type(item["sequence"]) is not int or item["sequence"] < 1
            ):
                raise ValueError("重做判断顺序不正确")
            if not isinstance(question, dict) or not isinstance(
                question.get("stem"), str
            ):
                raise ValueError("重做题目快照不正确")
            check_pdf_version(question, course)
            check_images(question.get("illustrations", []), course)
            if item["status"] == "COMPLETED":
                from datetime import datetime

                if (
                    type(item.get("correct")) is not bool
                    or not datetime.fromisoformat(item.get("completed_at", "")).tzinfo
                ):
                    raise ValueError("重做完成时间或判断不正确")
    return decoded


def apply(db, decoded):
    contract.apply(db, MODELS, decoded)
    from .bank_question_types import convert_sources

    convert_sources(db, [q["id"] for q in decoded["past_questions"]])


def upgrade_legacy(tables):
    """Only called for explicitly accepted old archive versions."""
    for table, fields in {
        "past_papers": {"bank_meta_json": "{}"},
        "past_questions": {"bank_data_json": "{}", "revision": 1},
        "exam_attempts": {"snapshot_json": "{}", "grading_json": "{}"},
    }.items():
        for row in tables.get(table, []):
            for key, value in fields.items():
                row.setdefault(key, value)


def upgrade_legacy_analysis(tables):
    tables.setdefault("exam_analysis_reports", [])
    for row in tables.get("topics", []):
        row.setdefault("revision", 1)
        row.setdefault("merged_into_id", None)
        row.setdefault("sources_json", "{}")

"""Build and round-trip real course packages for note reading/model acceptance.

Uses disposable accounts, SQLite and storage; never contacts a model or live app.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from uuid import uuid4
import zipfile

from generate_portable_samples import ROOT, all_selection, checked, seed


GUIDE = """# 阅读与笔记助手验收

本课程全部为自制测试资料，不含真实账号、密钥、作业或个人报告。

1. 在课程总览 → 标准数据包导入 `01-笔记阅读与AI助手验收课程.zip`，选择新建课程并核对预览。
2. 再导入 `02-跨课程导航补充.zip` 为另一门课程。
3. 打开本说明 → 阅读模式 → 专注阅读，默认“全部笔记”可按课程、目录、标题筛选。
4. 选择“分页检验”目录；应有32篇，可翻到第二页。筛选父目录应包含子目录，未归档可单独查找。
5. 在专注窗口切换笔记，再切换到补充课程，保持阅读状态；“本篇目录”定位当前文章标题。
6. 打开“A TCP与UDP对比”：核对图片、表格、双链和资料引用；双链应指向导入的新副本。
7. 返回编辑，默认不自动保存；修改后切换笔记，取消离开时正文保留。可按个人需要开启自动保存。
8. 在“API接入”保留的智谱区或新增的其他模型区配置自己的密钥；也可用页面上方“配置更多模型”。
9. 保存配置本身不调用模型；明确勾选连接测试后才发短文本。课程包没有附带任何可用密钥。
10. 打开“01-事务与并发”，选择一段正文，点“笔记AI”，分别试摘要、解释、整理、复习问题、自定要求。
11. 先预览实际发送文字、模型和地址，勾选同意后生成。检查答案，再追加或替换选区；撤销/重做可恢复。
12. 采纳不会强制保存；手动模式需点“立即保存”。开启自动保存时沿当前保存设置执行。
13. 生成中关闭窗口、切换模型或编辑正文后，旧结果不得覆盖当前笔记；失败保留输入，重新预览再试。
14. 验证原AI学习/题库仍可选择模型。纯文字模型不可用于图片请求，已有发送预览在切换后重新核对。
15. 可将本包再次合并到已有课程：新增副本，不覆盖原课程信息或原笔记；同名目录安全区分。

真实模型调用可能计费，输出质量需人工核对。自动验证只使用模拟响应；未代签人工验收。
"""

STUDY_NOTES = {
    "01-事务与并发": r"""# 事务与并发

## 四个性质
原子性要求事务要么全部完成，要么全部不发生；一致性是应用约束保持成立；隔离性约束并发可见行为；持久性保证已提交结果不因后续故障丢失。

## 一个并发例子
账户初始余额100，两个事务分别读到100，然后分别加20和减10，若后写覆盖前写，结果可能是90或120，而非串行结果110。这是丢失更新的例子。

|现象|观察|改进方向|
|---|---|---|
|脏读|读取未提交写入|限制读取可见版本|
|不可重复读|同一行两次读取不同|核对隔离级别与快照|
|丢失更新|旧值覆盖新值|乐观版本检查或锁|

## 公式与代码
冲突检测可写成 $revision_{client}=revision_{server}$。

```sql
UPDATE notes SET revision = revision + 1
WHERE id = :id AND revision = :expected;
```

## 复习
- [ ] 区分脏读与丢失更新。
- [ ] 解释为什么受影响行数为0时要重新核对。
- [ ] 用自己的话描述乐观锁的适用场景。
""",
    "02-网络分层": r"""# 网络分层与传输

## 分层职责
应用层规定应用消息；传输层提供进程间通信；网络层负责跨网络寻址和转发；链路层负责相邻节点之间传输。

## TCP与UDP
TCP提供有序可靠字节流，UDP提供数据报。应用选择取决于延迟、顺序、可靠性等要求，不能简单说一种始终更快。

## 时延估计
发送时延为 $t_s=L/R$，传播时延为 $t_p=d/v$。它们不包括排队和处理时延。

$$t_{total}=t_s+t_p+t_q+t_{proc}$$

## 自测
某链路传输8000 bit数据、速率为1 Mbps，发送时延为8 ms。传播距离增加不会直接改变该发送时延。
""",
    "03-结构整理练习": r"""数据库整理用的散记：索引可提高部分查询效率，但是增加维护开销。不要把索引等同于主键。

事务要考虑并发和故障；下面SQL是参数化示意，不含真实账号数据。
```sql
SELECT title FROM notes WHERE course_id = :course;
```
要保留这个公式：$T(n)=O(log n)$。实际索引成本还取决于数据分布、页访问和执行计划。

待做：先列概念，再列例子，再列复习问题；不应把我的猜测写成确定结论。
""",
}


def generate(client, output):
    from sqlalchemy import select
    from app.core.database import SessionLocal
    from app.models import (
        Asset,
        Citation,
        Course,
        Document,
        DocumentChunk,
        DocumentVersion,
        Note,
    )

    headers, fixture = seed(client)

    def call(method, path, **kwargs):
        return checked(
            client.request(method, "/api/v1" + path, headers=headers, **kwargs)
        )

    cid = fixture["course"]["id"]
    call(
        "PATCH",
        f"/courses/{cid}",
        json={
            "revision": fixture["course"]["revision"],
            "name": "笔记阅读与AI助手验收课程",
            "description": "自制验收课程：40篇笔记、分层目录、图片、资料引用及分页样例。",
        },
    )
    study = call(
        "POST", "/note-folders", json={"course_id": cid, "name": "学习与AI练习"}
    )
    nested = call(
        "POST",
        "/note-folders",
        json={"course_id": cid, "parent_id": study["id"], "name": "结构整理"},
    )
    paging = call("POST", "/note-folders", json={"course_id": cid, "name": "分页检验"})
    for title, content in STUDY_NOTES.items():
        call(
            "POST",
            "/notes",
            json={
                "course_id": cid,
                "folder_id": nested["id"] if title.startswith("03") else study["id"],
                "title": title,
                "content": content,
                "tags": ["验收", "AI练习"],
            },
        )
    for number in range(1, 33):
        call(
            "POST",
            "/notes",
            json={
                "course_id": cid,
                "folder_id": paging["id"],
                "title": f"分页笔记{number:02d}",
                "content": f"# 分页笔记{number:02d}\n\n这是第{number}篇导航测试样例；点击后应显示对应编号。\n\n## 检查点\n\n目录筛选、翻页、标题搜索及专注窗口内切换。",
                "tags": ["分页样例"],
            },
        )
    call(
        "POST",
        "/notes",
        json={
            "course_id": cid,
            "title": "00-先读我-验收步骤",
            "content": GUIDE,
            "tags": ["操作说明"],
        },
    )
    other = call(
        "POST",
        "/courses",
        json={
            "name": "跨课程导航补充",
            "description": "用于在专注阅读内切换到另一门课程。",
        },
    )
    call(
        "POST",
        "/notes",
        json={
            "course_id": other["id"],
            "title": "其他课程-调度速记",
            "content": "# 调度速记\n\n此笔记属于另一门课程。专注阅读的全部课程筛选应能找到它。\n\n## 轮转调度\n\n时间片控制连续运行时长，切换开销和响应时间需权衡。",
            "tags": ["跨课程验收"],
        },
    )
    summaries = []

    def export_and_check(source, filename):
        catalog = call(
            "GET", f"/courses/{source}/packages/catalog", params={"kind": "course"}
        )
        payload = {
            "course_id": source,
            "kind": "course",
            "selection": all_selection(catalog),
        }
        preview = call("POST", "/packages/selection-preview", json=payload)
        payload["expected_sha256"] = preview["selection_sha256"]
        response = client.post("/api/v1/packages/export", headers=headers, json=payload)
        if response.status_code != 200:
            raise RuntimeError(f"Export failed ({response.status_code})")
        raw = response.content
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            assert archive.testzip() is None
            members = len(archive.namelist())
        viewed = call(
            "POST",
            "/packages/preview",
            files={"file": (filename, raw, "application/zip")},
        )

        def imported(target=None):
            request = {
                "preview_id": viewed["preview_id"],
                "selection": all_selection(viewed),
            }
            if target:
                request["target_course_id"] = target
            scope = call("POST", "/packages/selection-preview", json=request)
            request.update(
                request_id=str(uuid4()), expected_sha256=scope["selection_sha256"]
            )
            result = call("POST", "/packages/import", json=request)
            assert call("POST", "/packages/import", json=request) == result
            return result

        result = imported()
        target = result["course_id"]
        assert target != source
        with SessionLocal() as db:
            originals = db.scalars(select(Note).where(Note.course_id == source)).all()
            copies = db.scalars(select(Note).where(Note.course_id == target)).all()
            assert sorted(n.title for n in originals) == sorted(n.title for n in copies)
            assert {n.id for n in originals}.isdisjoint(n.id for n in copies)
            for note in copies:
                for target_id in re.findall(r"\[\[note:([0-9a-f-]{36})", note.content):
                    assert db.get(Note, target_id).course_id == target
                for target_id in re.findall(r"\[\[asset:([0-9a-f-]{36})", note.content):
                    asset = db.get(Asset, target_id)
                    assert (
                        asset.course_id == target and Path(asset.storage_path).is_file()
                    )
                for citation in db.scalars(
                    select(Citation).where(Citation.note_id == note.id)
                ):
                    chunk = db.get(DocumentChunk, citation.chunk_id)
                    version = db.get(DocumentVersion, citation.version_id)
                    assert (
                        chunk.version_id == version.id and citation.quote in chunk.text
                    )
                    assert db.get(Document, version.document_id).course_id == target
            before = {n.id: n.content for n in copies}
            original_name = db.get(Course, target).name
        merged = imported(target)
        assert merged["course_id"] == target and merged["counts"].get("courses", 0) == 0
        with SessionLocal() as db:
            after = db.scalars(select(Note).where(Note.course_id == target)).all()
            assert len(after) == 2 * len(before)
            assert all(
                db.get(Note, nid).content == body for nid, body in before.items()
            )
            assert db.get(Course, target).name == original_name
        (output / filename).write_bytes(raw)
        summaries.append(
            {
                "file": filename,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size_bytes": len(raw),
                "zip_members": members,
                "counts": result["counts"],
                "roundtrip": "passed",
                "relations_and_assets": "passed",
                "merge_without_overwrite": "passed",
                "idempotency": "passed",
            }
        )

    export_and_check(cid, "01-笔记阅读与AI助手验收课程.zip")
    export_and_check(other["id"], "02-跨课程导航补充.zip")
    (output / "课程包验收说明.txt").write_text(GUIDE, encoding="utf-8")
    (output / "课程包验证结果.json").write_text(
        json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT.parent / "Hustudy验收样例" / "多模型与笔记助手-20261027",
    )
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if output == ROOT or ROOT in output.parents:
        parser.error("验收样例必须生成在工程外。")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="hustudy-note-assistant-samples-"
    ) as scratch:
        os.environ.update(
            {
                "HUSTUDY_DATABASE_URL": "sqlite:///"
                + (Path(scratch) / "samples.db").as_posix(),
                "HUSTUDY_STORAGE_ROOT": str(Path(scratch) / "storage"),
                "HUSTUDY_JWT_SECRET": "isolated-note-assistant-course-samples-2026",
                "HUSTUDY_WORKER_AUTOSTART": "false",
                "HUSTUDY_LLM_PROVIDER": "mock",
                "HUSTUDY_ZHIPU_API_KEY": "",
                "HUSTUDY_LIBREOFFICE_PATH": "/nonexistent/sample-office",
            }
        )
        sys.path.insert(0, str(ROOT / "backend"))
        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import engine

        try:
            with TestClient(app) as client:
                summaries = generate(client, output)
        finally:
            engine.dispose()
    print(
        json.dumps(
            {"output": str(output), "status": "verified", "packages": summaries},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

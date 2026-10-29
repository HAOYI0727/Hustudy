"""Build acceptance ZIPs through the real API in a disposable database.

No connection to the running application, real account, or model provider is made.
The output directory must be outside the repository. Each run gets its own folder.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from uuid import uuid4
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def checked(response, expected=(200, 201, 202)):
    if response.status_code not in expected:
        raise RuntimeError(
            f"Sample API failed ({response.status_code}): {response.text[:700]}"
        )
    return response.json()


def seed(client):
    """Create only self-authored fixtures using ordinary public business routes."""
    from PIL import Image, ImageDraw
    from app.workers.materials import drain_jobs

    account = checked(
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "package_sample_" + uuid4().hex[:12],
                "password": "Disposable-package-samples-only-2026",
            },
        )
    )
    headers = {"Authorization": "Bearer " + account["access_token"]}

    def call(method, path, **kwargs):
        return checked(
            client.request(method, "/api/v1" + path, headers=headers, **kwargs)
        )

    course = call(
        "POST",
        "/courses",
        json={
            "name": "标准包验收 · 计算机网络",
            "description": "自制样例：目录、双链、图片、资料引用、题库和练习。",
            "category": "验收样例",
            "tags": ["标准数据包", "计算机网络"],
        },
    )
    cid = course["id"]
    root = call(
        "POST", "/note-folders", json={"course_id": cid, "name": "第一章 网络基础"}
    )
    nested = call(
        "POST",
        "/note-folders",
        json={"course_id": cid, "parent_id": root["id"], "name": "协议对比"},
    )
    empty = call(
        "POST", "/note-folders", json={"course_id": cid, "name": "空目录（应保留）"}
    )
    material = "# 计算机网络自制讲义\n\nTCP提供可靠的字节流传输。UDP提供无连接的数据报传输。\n\n窗口机制调节发送速率。"
    job = call(
        "POST",
        f"/courses/{cid}/documents",
        files={"file": ("网络基础讲义.md", material.encode(), "text/markdown")},
    )
    drain_jobs()
    chunks = call("GET", f"/versions/{job['resource_id']}/chunks")
    chunk = next(row for row in chunks if "TCP提供可靠" in row["text"])
    image = Image.new("RGB", (520, 200), "#f5f3ff")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((20, 60, 165, 145), 12, fill="#6251c6")
    draw.rounded_rectangle((355, 60, 500, 145), 12, fill="#2b8b83")
    draw.line((180, 100, 335, 100), fill="#26304b", width=6)
    draw.polygon([(335, 100), (315, 88), (315, 112)], fill="#26304b")
    draw.text((55, 95), "CLIENT", fill="white")
    draw.text((395, 95), "SERVER", fill="white")
    binary = io.BytesIO()
    image.save(binary, format="PNG")
    asset = call(
        "POST",
        f"/courses/{cid}/assets",
        files={"file": ("客户端与服务器.png", binary.getvalue(), "image/png")},
    )
    call(
        "POST",
        f"/courses/{cid}/assets",
        files={"file": ("未引用图片.png", binary.getvalue(), "image/png")},
    )

    def note(title, content, folder=None, citations=None):
        return call(
            "POST",
            "/notes",
            json={
                "course_id": cid,
                "folder_id": folder,
                "title": title,
                "content": content,
                "tags": ["样例", "网络"],
                "citations": citations or [],
            },
        )

    b = note(
        "B UDP速记",
        "# UDP速记\n\n- 无连接\n- 面向数据报\n\n$$R=\\frac{L}{t}$$\n",
        nested["id"],
    )
    a = note(
        "A TCP与UDP对比",
        f"# TCP与UDP对比\n\nTCP提供可靠的字节流传输。\n\n![[asset:{asset['id']}|客户端与服务器]]\n\n[[note:{b['id']}|查看UDP速记]]\n\n|协议|特点|\n|---|---|\n|TCP|可靠字节流|\n|UDP|无连接数据报|\n",
        root["id"],
        [
            {
                "version_id": chunk["version_id"],
                "chunk_id": chunk["id"],
                "quote": "TCP提供可靠的字节流传输。",
            }
        ],
    )
    b = call(
        "PATCH",
        f"/notes/{b['id']}",
        json={
            "revision": b["revision"],
            "content": b["content"] + f"\n[[note:{a['id']}|返回对比笔记]]\n",
        },
    )
    loose = note(
        "C 未归档速记",
        "# 未归档速记\n\n没有加入文件夹的笔记也应正常迁移。\n\n- [x] 检查中文标题\n- [ ] 检查导出后重新导入\n",
    )
    same = note(
        "B UDP速记",
        "# 同名笔记\n\n此笔记与子目录内的 B UDP速记同名，但内容和位置不同，应同时保留。\n",
    )
    paper = call(
        "POST",
        f"/courses/{cid}/question-bank/import",
        json={
            "title": "自制网络基础小测",
            "content": "1. 哪个协议提供可靠的字节流传输？\nA. IP B. TCP C. ARP D. UDP\n答案：B\n知识标签：网络基础",
        },
    )
    call("POST", f"/past-papers/{paper['id']}/confirm")
    topic = call("GET", f"/courses/{cid}/topics")[0]
    exam = call(
        "POST",
        f"/courses/{cid}/question-bank/draw",
        json={
            "request_id": str(uuid4()),
            "topic_ids": [topic["id"]],
            "count": 1,
            "question_type": "single_choice",
        },
    )
    call("POST", f"/exam-papers/{exam['id']}/review")
    answers = call("GET", f"/exam-papers/{exam['id']}?include_answers=true")
    question = answers["questions"][0]
    attempt = call("POST", f"/exam-papers/{exam['id']}/attempts")
    wrong = next(choice for choice in "ABCD" if choice != question["answer"])
    call(
        "PUT",
        f"/attempts/{attempt['id']}/answers/{question['id']}",
        json={"answer": wrong},
    )
    call("POST", f"/attempts/{attempt['id']}/submit")
    mistakes = call("GET", "/mistakes")
    call(
        "POST",
        "/review-tasks",
        json={
            "mistake_id": mistakes[0]["id"],
            "title": "复习：TCP与UDP区别",
            "due_date": "2026-11-05",
        },
    )
    # Demo mode is local and deterministic; this never requests a remote model.
    call(
        "POST",
        f"/courses/{cid}/ai-queries",
        json={"mode": "demo", "query": "TCP与UDP有哪些区别？"},
    )
    return headers, {
        "course": course,
        "root": root,
        "nested": nested,
        "empty": empty,
        "a": a,
        "b": b,
        "loose": loose,
        "same": same,
    }


def all_selection(catalog):
    result = {}
    for row in catalog["items"]:
        result.setdefault(row["category"], []).append(row["id"])
    return result


def generate(client, output):
    headers, data = seed(client)
    cid = data["course"]["id"]
    summaries = []

    def export(
        filename, kind="course", selection=None, folder=None, source_course=None
    ):
        export_course = source_course or cid
        params = {"kind": kind}
        if folder:
            params["folder_id"] = folder
        catalog = checked(
            client.get(
                f"/api/v1/courses/{export_course}/packages/catalog",
                headers=headers,
                params=params,
            )
        )
        payload = {
            "course_id": export_course,
            "kind": kind,
            "selection": selection if selection is not None else all_selection(catalog),
        }
        if folder:
            payload["folder_id"] = folder
        checked_scope = checked(
            client.post(
                "/api/v1/packages/selection-preview", headers=headers, json=payload
            )
        )
        payload["expected_sha256"] = checked_scope["selection_sha256"]
        response = client.post("/api/v1/packages/export", headers=headers, json=payload)
        if response.status_code != 200:
            raise RuntimeError(f"Export failed: {response.text[:700]}")
        raw = response.content
        (output / filename).write_bytes(raw)
        preview = checked(
            client.post(
                "/api/v1/packages/preview",
                headers=headers,
                files={"file": (filename, raw, "application/zip")},
            )
        )
        # Every positive sample is actually re-imported, in the isolated database.
        request = {
            "preview_id": preview["preview_id"],
            "request_id": str(uuid4()),
            "selection": all_selection(preview),
        }
        if kind == "folder":
            target = checked(
                client.post(
                    "/api/v1/courses",
                    headers=headers,
                    json={"name": "隔离样例回导目标"},
                )
            )
            request["target_course_id"] = target["id"]
        reviewed = checked(
            client.post(
                "/api/v1/packages/selection-preview",
                headers=headers,
                json={
                    key: value for key, value in request.items() if key != "request_id"
                },
            )
        )
        request["expected_sha256"] = reviewed["selection_sha256"]
        result = checked(
            client.post("/api/v1/packages/import", headers=headers, json=request)
        )
        replay = checked(
            client.post("/api/v1/packages/import", headers=headers, json=request)
        )
        if result != replay:
            raise RuntimeError("Idempotent replay returned a different result")
        summaries.append(
            {
                "file": filename,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size_bytes": len(raw),
                "kind": kind,
                "counts": result["counts"],
                "warnings": result.get("warnings", []),
                "roundtrip": "passed",
                "idempotency": "passed",
            }
        )
        return raw

    full = export("01-完整课程-网络基础.zip")
    export("02-笔记文件夹-含子目录与图片.zip", "folder", folder=data["root"]["id"])
    export(
        "03-自选笔记-A和未归档C.zip",
        "folder",
        {"notes": [data["a"]["id"], data["loose"]["id"]]},
    )
    export(
        "04-仅题库与练习.zip",
        selection={
            "past_papers": all_selection(
                checked(
                    client.get(
                        f"/api/v1/courses/{cid}/packages/catalog",
                        headers=headers,
                        params={"kind": "course"},
                    )
                )
            ).get("past_papers", []),
            "exam_papers": all_selection(
                checked(
                    client.get(
                        f"/api/v1/courses/{cid}/packages/catalog",
                        headers=headers,
                        params={"kind": "course"},
                    )
                )
            ).get("exam_papers", []),
        },
    )
    export("05-空目录.zip", "folder", {"folders": [data["empty"]["id"]]})
    with zipfile.ZipFile(io.BytesIO(full)) as source:
        members = {info.filename: source.read(info) for info in source.infolist()}
    bad = io.BytesIO()
    with zipfile.ZipFile(bad, "w", zipfile.ZIP_STORED) as archive:
        for name, body in members.items():
            archive.writestr(name, body)
        archive.writestr("../不应写出的文件.txt", "安全验收：必须拒绝整个包")
    invalid_name = "06-异常样例-路径越界-应拒绝.zip"
    (output / invalid_name).write_bytes(bad.getvalue())
    response = client.post(
        "/api/v1/packages/preview",
        headers=headers,
        files={"file": (invalid_name, bad.getvalue(), "application/zip")},
    )
    if response.status_code not in (400, 413, 422):
        raise RuntimeError(f"Unsafe sample was not rejected: {response.status_code}")
    summaries.append(
        {
            "file": invalid_name,
            "expected": "拒绝整包，业务数据不变",
            "automated_rejection": response.status_code,
        }
    )
    supplement = checked(
        client.post(
            "/api/v1/courses",
            headers=headers,
            json={
                "name": "补充课程包 · DNS",
                "description": "合并时此简介不应覆盖目标课程。",
                "category": "补充来源",
                "tags": ["DNS"],
            },
        )
    )
    extra_folder = checked(
        client.post(
            "/api/v1/note-folders",
            headers=headers,
            json={"course_id": supplement["id"], "name": data["root"]["name"]},
        )
    )
    checked(
        client.post(
            "/api/v1/notes",
            headers=headers,
            json={
                "course_id": supplement["id"],
                "folder_id": extra_folder["id"],
                "title": data["a"]["title"],
                "content": "# 合并样例：同名的新笔记\n\n这是补充课程的DNS内容，不应覆盖原TCP笔记。\n\nDNS把域名映射为IP地址。",
                "tags": ["合并样例", "DNS"],
            },
        )
    )
    merged_raw = export(
        "07-合并课程包-同名目录与笔记.zip", source_course=supplement["id"]
    )
    merged_preview = checked(
        client.post(
            "/api/v1/packages/preview",
            headers=headers,
            files={"file": ("合并样例.zip", merged_raw, "application/zip")},
        )
    )
    merge_request = {
        "preview_id": merged_preview["preview_id"],
        "request_id": str(uuid4()),
        "selection": all_selection(merged_preview),
        "target_course_id": cid,
    }
    merged = checked(
        client.post("/api/v1/packages/import", headers=headers, json=merge_request)
    )
    if merged["course_id"] != cid or merged["counts"].get("courses", 0) != 0:
        raise RuntimeError("Course merge unexpectedly created a course")
    if (
        checked(
            client.post("/api/v1/packages/import", headers=headers, json=merge_request)
        )
        != merged
    ):
        raise RuntimeError("Course merge replay was not idempotent")
    original_note = checked(
        client.get(f"/api/v1/notes/{data['a']['id']}", headers=headers)
    )
    if original_note["content"] != data["a"]["content"]:
        raise RuntimeError("Course merge overwrote the original note")
    summaries[-1]["merge_into_existing"] = "passed"
    summaries[-1]["merge_counts"] = merged["counts"]
    (output / "预期结果.json").write_text(
        json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "先读我.txt").write_text(
        "Hustudy 标准数据包验收样例\n\n"
        "所有内容均为自制样例，生成和回导检查只使用临时数据库，不接触日常账户。\n"
        "1. 在课程总览导入01：预览全部内容，确认后检查课程分类/标签、4篇笔记、3个目录、2张图片、1份资料、题库、练习与错题复习。\n"
        "2. 在笔记工作区导入02到指定课程：应包含第一章/协议对比及A、B两篇笔记，图片正常，双链指向新副本。\n"
        "3. 导入03：只包含A与未归档C，A的目录及引用图片随包；B不导入，原双链显示普通文字，不回跳源笔记。\n"
        "4. 导入04：题库和练习及必要依赖可查看，不增加A/B/C笔记。\n"
        "5. 导入05：保留空目录，笔记数量不增加。\n"
        "6. 选择06：显示错误；不应创建课程或笔记。\n"
        "7. 导入07时选择“合并到已有课程”，目标选择01导入的网络课程：应新增1篇同名DNS笔记和1个自动区分名称的文件夹；原课程名称/简介/标签及原TCP笔记保持不变。\n"
        "8. 从网页重新导出已导入的课程/文件夹，再导入核对；同名对象创建副本，不覆盖原内容。\n"
        "9. 自选内容时先看预览的依赖与省略说明，再确认。关闭预览不应导入。可依次把多个来源课程包合并到同一目标课程。\n\n"
        "详细计数、文件哈希及自动回导结果见预期结果.json。人工验收仍需实际操作。\n",
        encoding="utf-8",
    )
    return summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT.parent / "Hustudy验收样例")
    args = parser.parse_args()
    destination = args.output.expanduser().resolve()
    if destination == ROOT or ROOT in destination.parents:
        parser.error("测试样例必须放在工程外；默认位于项目旁的 Hustudy验收样例。")
    output = destination / (
        "标准数据包-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:6]
    )
    output.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="hustudy-package-samples-") as scratch:
        os.environ.update(
            {
                "HUSTUDY_DATABASE_URL": "sqlite:///"
                + (Path(scratch) / "samples.db").as_posix(),
                "HUSTUDY_STORAGE_ROOT": str(Path(scratch) / "storage"),
                "HUSTUDY_JWT_SECRET": "isolated-package-samples-no-real-account-2026",
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
            {"output": str(output), "samples": len(summaries), "status": "verified"},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

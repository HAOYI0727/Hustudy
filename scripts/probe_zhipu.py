"""Opt-in live check: synthetic text only, no database or private documents."""

import argparse
import json
from uuid import uuid4
from app.ai.providers import ZhipuProvider, ProviderFailure
from app.core.config import get_settings


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-synthetic-send", action="store_true")
    args = parser.parse_args()
    if not args.confirm_synthetic_send:
        parser.error("Pass --confirm-synthetic-send to send the self-authored test.")
    source = {
        "source_id": str(uuid4()),
        "version_id": str(uuid4()),
        "document_id": str(uuid4()),
        "locator": {"type": "heading", "value": "自制联通样例"},
        "source_kind": "extracted",
        "text": "这是Hustudy自制测试：两个苹果加三个苹果，总共五个苹果。",
    }
    try:
        result, status = ZhipuProvider(get_settings()).answer(
            "根据自制测试，两个加三个苹果共有多少个？只依据原文回答。", [source]
        )
        print(
            json.dumps(
                {
                    "status": status,
                    "model": result["model"],
                    "citation_count": len(result["citations"]),
                    "usage": result.get("usage", {}),
                },
                ensure_ascii=False,
            )
        )
    except ProviderFailure as error:
        print(
            json.dumps(
                {
                    "status": "provider_error",
                    "code": error.code,
                    "message": error.message,
                },
                ensure_ascii=False,
            )
        )
        raise SystemExit(1)

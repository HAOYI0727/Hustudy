from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.ai.providers import ProviderFailure, checked_evidence


def test_citation_rejects_unknown_id_without_leaking_model_values():
    evidence = SimpleNamespace(source_id=uuid4(), quote="untrusted-model-text")
    with pytest.raises(ProviderFailure) as caught:
        checked_evidence([evidence], [])
    assert caught.value.code == "INVALID_CITATION"
    assert "片段ID不在本次发送范围" in caught.value.message
    assert evidence.quote not in caught.value.message
    assert str(evidence.source_id) not in caught.value.message


def test_citation_rejects_whitespace_rewrite_without_fuzzy_matching():
    source_id = str(uuid4())
    evidence = SimpleNamespace(source_id=source_id, quote="nowhere")
    with pytest.raises(ProviderFailure) as caught:
        checked_evidence([evidence], [{"source_id": source_id, "text": "now here"}])
    assert caught.value.code == "INVALID_CITATION"
    assert "摘录与对应片段原文不一致" in caught.value.message
    assert evidence.quote not in caught.value.message

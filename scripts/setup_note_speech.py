"""Explicit public model download; never executed by a recognition job."""

from pathlib import Path
import os

os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ["HF_HUB_ETAG_TIMEOUT"] = "20"
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "30"


def main():
    from huggingface_hub import HfApi, snapshot_download

    repo = "Systran/faster-whisper-base"
    target = (
        Path(__file__).resolve().parents[1] / "data" / "models" / "faster-whisper-base"
    )
    info = HfApi(token=False).model_info(repo)
    snapshot_download(
        repo,
        revision=info.sha,
        token=False,
        local_dir=target,
        allow_patterns=[
            "config.json",
            "model.bin",
            "tokenizer.json",
            "vocabulary.*",
            "preprocessor_config.json",
            "README.md",
            "LICENSE*",
        ],
        max_workers=2,
    )
    (target / "source-revision.txt").write_text(
        f"{repo}\n{info.sha}\nMIT; see model card and upstream Whisper license.\n",
        encoding="utf-8",
    )
    print("Local speech model ready. Restart the worker.")


if __name__ == "__main__":
    main()

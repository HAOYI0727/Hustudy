"""Local recognition only. Called in a bounded worker subprocess."""

from pathlib import Path
import json
import sys
import zipfile

MAX_TEXT = 100_000


def ocr(image):
    try:
        from rapidocr_onnxruntime import RapidOCR
        import numpy as np
    except ImportError:
        raise ValueError(
            "未安装本地OCR组件，请安装backend/requirements-capture.txt并重启worker"
        ) from None
    result, _ = RapidOCR()(np.asarray(image.convert("RGB")))
    return "\n".join(row[1] for row in (result or []))


def recognize(path: Path):
    parts, warnings = [], []
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(path)
        if reader.is_encrypted:
            raise ValueError("请先解密PDF后重新导入")
        if len(reader.pages) > 40:
            raise ValueError("PDF最多40页，请拆分后导入")
        for index, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            method = "text"
            if not text.strip():
                try:
                    import pypdfium2 as pdfium
                except ImportError:
                    raise ValueError(
                        "扫描PDF需要安装backend/requirements-capture.txt"
                    ) from None
                document = pdfium.PdfDocument(str(path))
                try:
                    rendered = document[index]
                    width, height = rendered.get_size()
                    if width * height * 4 > 24_000_000:
                        raise ValueError("PDF页面尺寸超过识别预算")
                    bitmap = rendered.render(scale=2)
                    try:
                        text = ocr(bitmap.to_pil())
                    finally:
                        bitmap.close()
                        rendered.close()
                finally:
                    document.close()
                method = "ocr"
            parts.append(
                {"location": f"第{index + 1}页", "text": text, "method": method}
            )
            if not text.strip():
                warnings.append(f"第{index + 1}页未识别到文字，请人工核对")
    elif suffix == ".docx":
        with zipfile.ZipFile(path) as archive:
            if sum(info.file_size for info in archive.infolist()) > 64 * 1024 * 1024:
                raise ValueError("Word解压内容超过64MiB")
            has_images = any(
                info.filename.startswith("word/media/") for info in archive.infolist()
            )
        from docx import Document
        from docx.table import Table

        for index, block in enumerate(Document(path).iter_inner_content()):
            text = (
                "\n".join(
                    " | ".join(cell.text for cell in row.cells) for row in block.rows
                )
                if isinstance(block, Table)
                else block.text
            )
            if text.strip():
                parts.append(
                    {
                        "location": f"段落/表格{index + 1}",
                        "text": text,
                        "method": "text",
                    }
                )
        if has_images:
            warnings.append(
                "Word内嵌图片未识别，请另存图片后导入；页眉、页脚和文本框需人工核对"
            )
    elif suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        from PIL import Image, ImageOps

        with Image.open(path) as image:
            if image.width * image.height > 24_000_000:
                raise ValueError("图片最多2400万像素")
            parts.append(
                {
                    "location": "图片",
                    "text": ocr(ImageOps.exif_transpose(image)),
                    "method": "ocr",
                }
            )
    elif suffix in {".wav", ".mp3", ".m4a", ".webm", ".ogg", ".mp4"}:
        from ..core.config import get_settings

        try:
            import av
            from faster_whisper import WhisperModel
        except ImportError:
            raise ValueError(
                "未安装本地语音组件，请安装backend/requirements-capture.txt"
            ) from None
        model_path = Path(get_settings().speech_model_path)
        if not model_path.is_dir() or not (model_path / "model.bin").is_file():
            raise ValueError(
                "未配置本地Whisper模型，请按识别导入说明下载模型并设置HUSTUDY_SPEECH_MODEL_PATH"
            )
        # Decode only a bounded number of samples before model inference.
        import numpy as np

        samples, total = [], 0
        with av.open(str(path)) as container:
            resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
            for frame in container.decode(audio=0):
                for converted in resampler.resample(frame):
                    total += converted.samples
                    if total > 300 * 16000:
                        raise ValueError("音频最多5分钟，请截取后导入")
                    samples.append(converted.to_ndarray().reshape(-1))
            for converted in resampler.resample(None):
                total += converted.samples
                samples.append(converted.to_ndarray().reshape(-1))
        if total > 300 * 16000 or not samples:
            raise ValueError("音频为空或超过5分钟")
        audio = np.concatenate(samples).astype(np.float32) / 32768
        model = WhisperModel(
            str(model_path),
            device="cpu",
            compute_type="int8",
            local_files_only=True,
            cpu_threads=4,
        )
        segments, _ = model.transcribe(audio, beam_size=3, vad_filter=True)
        parts = [
            {
                "location": f"{s.start:.1f}–{s.end:.1f}秒",
                "text": s.text.strip(),
                "method": "speech",
            }
            for s in segments
        ]
    else:
        raise ValueError("不支持此格式；旧版.doc请转换为.docx")
    text = "\n\n".join(part["text"] for part in parts if part["text"].strip())
    if not any(part["text"].strip() for part in parts):
        raise ValueError("未识别到文字，请换清晰文件或手动录入")
    if len(text) > MAX_TEXT:
        raise ValueError("识别文本超过10万字，请拆分文件")
    return {
        "text": text,
        "parts": parts,
        "warnings": warnings
        + ["识别结果待人工核对，尤其是手写、公式、表格和专有名词。"],
    }


if __name__ == "__main__":
    try:
        output = {"result": recognize(Path(sys.argv[1]))}
    except ValueError as error:
        output = {"error": str(error)}
    except Exception:
        output = {"error": "文件损坏、格式不兼容或识别组件不可用，请检查文件与安装环境"}
    Path(sys.argv[2]).write_text(
        json.dumps(output, ensure_ascii=False), encoding="utf-8"
    )

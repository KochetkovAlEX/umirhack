"""Тонкая обёртка над dekanat_core для Django: обработка, вопросы, смена типа, картинки."""
from __future__ import annotations

import hashlib
import io
import logging

import numpy as np
from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image, ImageDraw

from dekanat_core import pipeline
from dekanat_core.config.schema import get_doc_type, load_doc_types
from dekanat_core.io.loader import MultiPageError, UnsupportedFileError, sniff_format
from dekanat_core.layout.lines import group_lines
from dekanat_core.models import DocumentResult
from dekanat_core.preprocess.pipeline import map_bbox_back

from .models import ProcessingResult, QuestionAnswer, UploadedDocument

log = logging.getLogger(__name__)

MIME = {"png": "image/png", "jpeg": "image/jpeg", "pdf": "application/pdf", "webp": "image/webp",
        "bmp": "image/bmp", "tiff": "image/tiff"}


class ProcessingError(Exception):
    pass


def doc_types_public() -> list[dict]:
    return [cfg.public_dict() for cfg in load_doc_types().values()]


def _png_bytes(rgb: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, format="PNG", optimize=True)
    return buf.getvalue()


PREVIEW_MAX_SIDE = 1400


def _jpeg_preview(rgb: np.ndarray, max_side: int = PREVIEW_MAX_SIDE, quality: int = 82) -> bytes:
    """Лёгкий JPEG для просмотра в браузере/Mini App (пропорции сохраняются, bbox масштабируются на клиенте)."""
    img = Image.fromarray(rgb)
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
    return buf.getvalue()


def _jpeg_bytes(img: Image.Image, quality: int = 85) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


@transaction.atomic
def process_upload(data: bytes, filename: str, doc_type: str = "auto", *, source: str = "web",
                   telegram_user_id: str = "") -> UploadedDocument:
    fmt = sniff_format(data)
    if fmt is None:
        raise ProcessingError("Поддерживаются JPG, PNG и одностраничный PDF")
    doc = UploadedDocument(original_name=filename[:255], mime=MIME.get(fmt, "application/octet-stream"),
                           size=len(data), sha256=hashlib.sha256(data).hexdigest(),
                           selected_type=doc_type or "auto", source=source, telegram_user_id=telegram_user_id)
    doc.file.save(filename or f"document.{fmt}", ContentFile(data), save=False)
    doc.save()
    try:
        result, ctx = pipeline.process_document(data, filename, None if doc_type in ("", "auto", None) else doc_type,
                                                first_page_only=False)
    except MultiPageError as exc:
        doc.status, doc.error = UploadedDocument.Status.ERROR, str(exc)
        doc.save()
        raise ProcessingError(str(exc)) from exc
    except UnsupportedFileError as exc:
        doc.status, doc.error = UploadedDocument.Status.ERROR, str(exc)
        doc.save()
        raise ProcessingError(str(exc)) from exc
    except KeyError as exc:
        doc.status, doc.error = UploadedDocument.Status.ERROR, str(exc)
        doc.save()
        raise ProcessingError(str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        log.exception("Ошибка обработки %s", doc.id)
        doc.status, doc.error = UploadedDocument.Status.ERROR, f"Не удалось обработать документ: {exc}"
        doc.save()
        raise ProcessingError(doc.error) from exc

    pr = ProcessingResult(document=doc, result=result.to_dict(), transform=np.asarray(ctx.matrix).tolist(),
                          original_size=list(ctx.original_rgb.shape[1::-1]))
    pr.normalized_image.save(f"{doc.id}/normalized.png", ContentFile(_png_bytes(ctx.normalized_rgb)), save=False)
    pr.preview_image.save(f"{doc.id}/preview.jpg", ContentFile(_jpeg_preview(ctx.normalized_rgb)), save=False)
    pr.original_preview.save(f"{doc.id}/original_preview.jpg", ContentFile(_jpeg_preview(ctx.original_rgb)), save=False)
    pr.save()
    doc.doc_type, doc.type_confidence = result.doc_type, result.type_confidence
    doc.status, doc.timings = UploadedDocument.Status.DONE, result.timings
    doc.save()
    return doc


def load_result(doc: UploadedDocument) -> DocumentResult:
    return DocumentResult.from_dict(doc.result.result)


def ask(doc: UploadedDocument, question: str) -> QuestionAnswer:
    result = load_result(doc)
    ans = pipeline.answer_question(result, question)
    return QuestionAnswer.objects.create(
        document=doc, question=question, answerable=ans.answerable, value=ans.value, answer=ans.answer,
        sources=ans.sources, intent=ans.intent, field_key=ans.field_key or "",
    )


def check(doc: UploadedDocument) -> QuestionAnswer:
    from dekanat_core.qa.answer_builder import COMPLETENESS_QUESTION

    return ask(doc, COMPLETENESS_QUESTION)


def normalized_rgb(doc: UploadedDocument) -> np.ndarray:
    with doc.result.normalized_image.open("rb") as fh:
        return np.asarray(Image.open(fh).convert("RGB"))


def ensure_previews(doc: UploadedDocument) -> None:
    """Для документов, обработанных до появления превью, — сгенерировать их лениво."""
    pr = doc.result
    if pr.preview_image and pr.original_preview:
        return
    if not pr.preview_image:
        pr.preview_image.save(f"{doc.id}/preview.jpg", ContentFile(_jpeg_preview(normalized_rgb(doc))), save=False)
    if not pr.original_preview:
        try:
            from dekanat_core.io.loader import load_bytes

            with doc.file.open("rb") as fh:
                rgb = load_bytes(fh.read(), doc.original_name, first_page_only=True).rgb
            pr.original_preview.save(f"{doc.id}/original_preview.jpg", ContentFile(_jpeg_preview(rgb)), save=False)
        except Exception:  # pragma: no cover
            pr.original_preview.save(f"{doc.id}/original_preview.jpg", ContentFile(_jpeg_preview(normalized_rgb(doc))), save=False)
    pr.save()


@transaction.atomic
def change_type(doc: UploadedDocument, new_type: str) -> UploadedDocument:
    """Сменить тип вручную: повторное извлечение по уже выполненному OCR (без повторного OCR)."""
    get_doc_type(new_type)  # KeyError для неизвестного типа
    old = load_result(doc)
    ctx = pipeline.ProcessingContext()
    ctx.normalized_rgb = normalized_rgb(doc)
    ctx.matrix = np.asarray(doc.result.transform)
    ctx.lines = group_lines(old.ocr_lines)
    meta = {"timings": old.timings, "quality": {k: v for k, v in old.quality.items() if k not in ("steps", "ocr")},
            "steps": old.quality.get("steps", []), "ocr": old.quality.get("ocr", {}), "warnings": []}
    result = pipeline.build_result(ctx, new_type, meta)
    pr = doc.result
    pr.result = result.to_dict()
    pr.save()
    doc.selected_type, doc.doc_type, doc.type_confidence = new_type, result.doc_type, 1.0
    doc.save()
    doc.questions.all().delete()  # прежние ответы относились к другому типу
    return doc


def field_boxes(doc: UploadedDocument) -> list[dict]:
    """bbox полей в координатах нормализованного и исходного изображения (для подсветки)."""
    result = load_result(doc)
    M = np.asarray(doc.result.transform)
    out = []
    for key, fv in result.fields.items():
        if not fv.bbox:
            continue
        out.append({
            "key": key, "label": fv.label, "found": fv.found, "kind": fv.kind, "bbox": list(fv.bbox),
            "label_bbox": list(fv.label_bbox) if fv.label_bbox else None,
            "polygon_original": map_bbox_back(fv.bbox, M),
        })
    return out


def _color(fv) -> tuple:
    if fv.kind == "mark":
        return (37, 99, 235) if fv.found else (220, 38, 38)
    return (22, 163, 74) if fv.found else (220, 38, 38)


def annotated_png(doc: UploadedDocument, only_key: str | None = None) -> bytes:
    result = load_result(doc)
    img = Image.fromarray(normalized_rgb(doc)).convert("RGB")
    draw = ImageDraw.Draw(img)
    w = max(2, img.width // 400)
    for key, fv in result.fields.items():
        if not fv.bbox or (only_key and key != only_key):
            continue
        x1, y1, x2, y2 = fv.bbox
        pad = max(4, (y2 - y1) // 4)
        draw.rectangle([x1 - pad, y1 - pad, x2 + pad, y2 + pad], outline=_color(fv), width=w)
    img.thumbnail((1800, 1800), Image.LANCZOS)
    return _jpeg_bytes(img, 85)


def crop_png(doc: UploadedDocument, key: str, context: float = 0.6) -> bytes | None:
    result = load_result(doc)
    fv = result.fields.get(key)
    if fv is None or not fv.bbox:
        return None
    img = Image.fromarray(normalized_rgb(doc)).convert("RGB")
    x1, y1, x2, y2 = fv.bbox
    if fv.label_bbox:
        x1, y1 = min(x1, fv.label_bbox[0]), min(y1, fv.label_bbox[1])
        x2, y2 = max(x2, fv.label_bbox[2]), max(y2, fv.label_bbox[3])
    h = max(20, y2 - y1)
    px, py = int(0.1 * img.width), int(context * h) + 12
    cx1, cy1 = max(0, x1 - px), max(0, y1 - py)
    cx2, cy2 = min(img.width, x2 + px), min(img.height, y2 + py)
    crop = img.crop((cx1, cy1, cx2, cy2))
    draw = ImageDraw.Draw(crop)
    bx1, by1, bx2, by2 = fv.bbox
    pad = max(3, h // 4)
    draw.rectangle([bx1 - cx1 - pad, by1 - cy1 - pad, bx2 - cx1 + pad, by2 - cy1 + pad], outline=_color(fv), width=3)
    crop.thumbnail((1200, 1200), Image.LANCZOS)
    return _jpeg_bytes(crop, 88)


def export_json(doc: UploadedDocument, document_id: str | None = None) -> dict:
    """Один документ в формате results.json (answers — из истории вопросов)."""
    result = load_result(doc)
    return {
        "document_id": document_id or str(doc.id),
        "document_type": result.doc_type,
        "fields": result.fields_plain(),
        "validation": {"status": result.validation.status, "missing_fields": list(result.validation.missing_fields),
                       "sources": list(result.validation.sources)},
        "answers": [{"question_id": f"{doc.id}-Q{i + 1}", "answerable": q.answerable, "value": q.value,
                     "answer": q.answer, "sources": q.sources} for i, q in enumerate(doc.questions.all())],
    }

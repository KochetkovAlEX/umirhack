from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# ---------- services.py: обработка в фоне ----------
p = ROOT / "backend" / "documents" / "services.py"
s = p.read_text(encoding="utf-8")
i = s.index("@transaction.atomic\ndef process_upload(")
j = s.index("def load_result(")
new = '''_executor = ThreadPoolExecutor(max_workers=int(os.environ.get("DEKANAT_WORKERS", "1")), thread_name_prefix="ocr")


def _fail(doc: UploadedDocument, message: str) -> None:
    doc.status, doc.error = UploadedDocument.Status.ERROR, message
    doc.save(update_fields=["status", "error"])


def run_processing(doc_id, data: bytes, filename: str, doc_type: str) -> None:
    """Собственно OCR/извлечение; выполняется в рабочем потоке или синхронно."""
    doc = UploadedDocument.objects.get(pk=doc_id)
    try:
        result, ctx = pipeline.process_document(data, filename, None if doc_type in ("", "auto", None) else doc_type,
                                                first_page_only=False)
    except (MultiPageError, UnsupportedFileError, KeyError) as exc:
        _fail(doc, str(exc.args[0] if exc.args else exc))
        return
    except Exception as exc:  # pragma: no cover
        log.exception("Ошибка обработки %s", doc.id)
        _fail(doc, f"Не удалось обработать документ: {exc}")
        return
    with transaction.atomic():
        pr = ProcessingResult(document=doc, result=result.to_dict(), transform=np.asarray(ctx.matrix).tolist(),
                              original_size=list(ctx.original_rgb.shape[1::-1]))
        pr.normalized_image.save(f"{doc.id}/normalized.png", ContentFile(_png_bytes(ctx.normalized_rgb)), save=False)
        pr.preview_image.save(f"{doc.id}/preview.jpg", ContentFile(_jpeg_preview(ctx.normalized_rgb)), save=False)
        pr.original_preview.save(f"{doc.id}/original_preview.jpg", ContentFile(_jpeg_preview(ctx.original_rgb)), save=False)
        pr.save()
        doc.doc_type, doc.type_confidence = result.doc_type, result.type_confidence
        doc.status, doc.timings = UploadedDocument.Status.DONE, result.timings
        doc.save()
    # вопрос/проверка, заданные вместе с загрузкой
    doc = UploadedDocument.objects.select_related("result").get(pk=doc_id)
    if doc.pending_question:
        ask(doc, doc.pending_question)
    elif doc.pending_check:
        check(doc)


def _worker(doc_id, data, filename, doc_type):
    try:
        run_processing(doc_id, data, filename, doc_type)
    finally:
        connection.close()


def process_upload(data: bytes, filename: str, doc_type: str = "auto", *, source: str = "web",
                   telegram_user_id: str = "", question: str = "", check: bool = False,
                   wait: bool = True) -> UploadedDocument:
    """Создать документ и обработать: синхронно (wait=True) или в фоне (статус processing -> done/error)."""
    fmt = sniff_format(data)
    if fmt is None:
        raise ProcessingError("Поддерживаются JPG, PNG и одностраничный PDF")
    doc = UploadedDocument(original_name=filename[:255], mime=MIME.get(fmt, "application/octet-stream"),
                           size=len(data), sha256=hashlib.sha256(data).hexdigest(),
                           selected_type=doc_type or "auto", source=source, telegram_user_id=telegram_user_id,
                           pending_question=(question or "").strip(), pending_check=bool(check))
    doc.file.save(filename or f"document.{fmt}", ContentFile(data), save=False)
    doc.save()
    if wait:
        run_processing(doc.pk, data, filename, doc_type)
        doc = UploadedDocument.objects.get(pk=doc.pk)
        if doc.status == UploadedDocument.Status.ERROR:
            raise ProcessingError(doc.error)
        return doc
    _executor.submit(_worker, doc.pk, data, filename, doc_type)
    return doc


'''
s = s[:i] + new + s[j:]
s = s.replace("import hashlib\nimport io\nimport logging\n",
              "import hashlib\nimport io\nimport logging\nimport os\nfrom concurrent.futures import ThreadPoolExecutor\n")
s = s.replace("from django.db import transaction\n", "from django.db import connection, transaction\n")
p.write_text(s, encoding="utf-8")

# ---------- views.py: async-режим ----------
p = ROOT / "backend" / "documents" / "views.py"
s = p.read_text(encoding="utf-8")
old = '''        f = ser.validated_data["file"]
        data = f.read()
        try:
            doc = services.process_upload(data, f.name, ser.validated_data.get("doc_type") or "auto",
                                          source=ser.validated_data.get("source", "web"),
                                          telegram_user_id=ser.validated_data.get("telegram_user_id", ""))
        except services.ProcessingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        answer = None
        q = (ser.validated_data.get("question") or "").strip()
        if q:
            answer = services.ask(doc, q)
        elif ser.validated_data.get("check"):
            answer = services.check(doc)
        doc = _doc(doc.pk)
        payload = DocumentSerializer(doc, context={"request": request}).data
        payload["answer"] = QuestionAnswerSerializer(answer).data if answer else None
        return Response(payload, status=status.HTTP_201_CREATED)'''
new = '''        f = ser.validated_data["file"]
        data = f.read()
        q = (ser.validated_data.get("question") or "").strip()
        check = bool(ser.validated_data.get("check"))
        # async=1: ответить сразу (202, status=processing), обработка в фоне — для медленных каналов/туннелей
        wait = str(request.data.get("async", "")).lower() not in ("1", "true", "yes")
        try:
            doc = services.process_upload(data, f.name, ser.validated_data.get("doc_type") or "auto",
                                          source=ser.validated_data.get("source", "web"),
                                          telegram_user_id=ser.validated_data.get("telegram_user_id", ""),
                                          question=q, check=check, wait=wait)
        except services.ProcessingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        if not wait:
            payload = DocumentSerializer(doc, context={"request": request}).data
            payload["answer"] = None
            return Response(payload, status=status.HTTP_202_ACCEPTED)
        doc = _doc(doc.pk)
        payload = DocumentSerializer(doc, context={"request": request}).data
        last = doc.questions.order_by("-created_at").first() if (q or check) else None
        payload["answer"] = QuestionAnswerSerializer(last).data if last else None
        return Response(payload, status=status.HTTP_201_CREATED)'''
assert old in s, "views.post not found"
s = s.replace(old, new)
p.write_text(s, encoding="utf-8")

# ---------- serializers.py: pending-поля в ответе ----------
p = ROOT / "backend" / "documents" / "serializers.py"
s = p.read_text(encoding="utf-8")
s = s.replace('''                  "status", "error", "source", "timings", "created_at", "result", "questions", "images"]''',
              '''                  "status", "error", "source", "timings", "pending_question", "pending_check", "created_at",
                  "result", "questions", "images"]''')
p.write_text(s, encoding="utf-8")
print("patched")

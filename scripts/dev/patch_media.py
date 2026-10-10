import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def patch(rel, pairs):
    p = ROOT / rel
    s = p.read_text(encoding="utf-8")
    for a, b in pairs:
        if a not in s:
            print("NOT FOUND in", rel, ":", a[:60])
            sys.exit(1)
        s = s.replace(a, b)
    p.write_text(s, encoding="utf-8")


patch("backend/documents/services.py", [
    ('''def _png_bytes(rgb: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, format="PNG", optimize=True)
    return buf.getvalue()''', '''def _png_bytes(rgb: np.ndarray) -> bytes:
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
    return buf.getvalue()'''),
    ('''    pr.normalized_image.save(f"{doc.id}/normalized.png", ContentFile(_png_bytes(ctx.normalized_rgb)), save=False)
    pr.save()''', '''    pr.normalized_image.save(f"{doc.id}/normalized.png", ContentFile(_png_bytes(ctx.normalized_rgb)), save=False)
    pr.preview_image.save(f"{doc.id}/preview.jpg", ContentFile(_jpeg_preview(ctx.normalized_rgb)), save=False)
    pr.original_preview.save(f"{doc.id}/original_preview.jpg", ContentFile(_jpeg_preview(ctx.original_rgb)), save=False)
    pr.save()'''),
    ('''        draw.rectangle([x1 - pad, y1 - pad, x2 + pad, y2 + pad], outline=_color(fv), width=w)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()''', '''        draw.rectangle([x1 - pad, y1 - pad, x2 + pad, y2 + pad], outline=_color(fv), width=w)
    img.thumbnail((1800, 1800), Image.LANCZOS)
    return _jpeg_bytes(img, 85)'''),
    ('''    draw.rectangle([bx1 - cx1 - pad, by1 - cy1 - pad, bx2 - cx1 + pad, by2 - cy1 + pad], outline=_color(fv), width=3)
    buf = io.BytesIO()
    crop.save(buf, format="PNG")
    return buf.getvalue()''', '''    draw.rectangle([bx1 - cx1 - pad, by1 - cy1 - pad, bx2 - cx1 + pad, by2 - cy1 + pad], outline=_color(fv), width=3)
    crop.thumbnail((1200, 1200), Image.LANCZOS)
    return _jpeg_bytes(crop, 88)'''),
    ('''def normalized_rgb(doc: UploadedDocument) -> np.ndarray:
    with doc.result.normalized_image.open("rb") as fh:
        return np.asarray(Image.open(fh).convert("RGB"))''', '''def normalized_rgb(doc: UploadedDocument) -> np.ndarray:
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
    pr.save()'''),
])

patch("backend/documents/views.py", [
    ('''class ImageView(View):
    def get(self, request, pk):
        doc = _doc(pk)
        variant = request.GET.get("variant", "normalized")
        if variant == "original":
            return FileResponse(doc.file.open("rb"), content_type=doc.mime or "application/octet-stream")
        if not hasattr(doc, "result") or not doc.result.normalized_image:
            raise Http404
        return FileResponse(doc.result.normalized_image.open("rb"), content_type="image/png")''', '''IMMUTABLE = "public, max-age=31536000, immutable"


class ImageView(View):
    def get(self, request, pk):
        doc = _doc(pk)
        variant = request.GET.get("variant", "preview")
        if variant == "original":
            resp = FileResponse(doc.file.open("rb"), content_type=doc.mime or "application/octet-stream")
        else:
            if not hasattr(doc, "result") or not doc.result.normalized_image:
                raise Http404
            if variant == "normalized":
                resp = FileResponse(doc.result.normalized_image.open("rb"), content_type="image/png")
            else:
                services.ensure_previews(doc)
                f = doc.result.original_preview if variant == "original_preview" else doc.result.preview_image
                resp = FileResponse(f.open("rb"), content_type="image/jpeg")
        resp["Cache-Control"] = IMMUTABLE
        return resp'''),
    ('''        return HttpResponse(services.annotated_png(doc, request.GET.get("field")), content_type="image/png")''',
     '''        resp = HttpResponse(services.annotated_png(doc, request.GET.get("field")), content_type="image/jpeg")
        resp["Cache-Control"] = IMMUTABLE
        return resp'''),
    ('''        if data is None:
            raise Http404("Для этого поля нет координат")
        return HttpResponse(data, content_type="image/png")''', '''        if data is None:
            raise Http404("Для этого поля нет координат")
        resp = HttpResponse(data, content_type="image/jpeg")
        resp["Cache-Control"] = IMMUTABLE
        return resp'''),
    ('''class ExportView(APIView):
    def get(self, request, pk):
        return Response(services.export_json(_doc(pk)))''', '''class ExportView(APIView):
    def get(self, request, pk):
        import json as _json

        data = services.export_json(_doc(pk))
        resp = HttpResponse(_json.dumps(data, ensure_ascii=False, indent=2), content_type="application/json; charset=utf-8")
        if request.GET.get("download"):
            resp["Content-Disposition"] = 'attachment; filename="%s.json"' % pk
        return resp'''),
])

patch("backend/documents/serializers.py", [
    ('''            "original": f"{base}/api/v1/documents/{obj.id}/image?variant=original",
            "normalized": f"{base}/api/v1/documents/{obj.id}/image?variant=normalized",''',
     '''            "original": f"{base}/api/v1/documents/{obj.id}/image?variant=original",
            "original_preview": f"{base}/api/v1/documents/{obj.id}/image?variant=original_preview",
            "normalized": f"{base}/api/v1/documents/{obj.id}/image?variant=normalized",
            "preview": f"{base}/api/v1/documents/{obj.id}/image?variant=preview",'''),
])
print("backend patched")

import sys; sys.path.insert(0, "core"); sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
from PIL import Image
from dekanat_core import pipeline
from dekanat_core.marks import detect as md
from dekanat_core.config.schema import get_doc_type
data = Path("scripts/dev/user_photo2.jpg").read_bytes()
res, ctx = pipeline.process_document(data, "photo.jpg", None)
print("type:", res.doc_type, res.type_confidence, "steps:", res.quality.get("steps"), "size:", res.image_size)
for k, v in res.fields.items(): print(f"  {k:18} {v.value!r:45} conf={v.confidence} bbox={v.bbox}")
print(res.validation.status, res.validation.missing_fields)
cfg = get_doc_type(res.doc_type)
seal = [f for f in cfg.mark_fields if f.type == "seal"][0]
det = md.detect_seal(ctx.normalized_rgb, ctx.lines, seal)
print("seal details:", det.details)
Image.fromarray(ctx.normalized_rgb).save("scripts/dev/user_photo2_norm.jpg", quality=85)

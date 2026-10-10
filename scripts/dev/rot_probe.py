import sys, json, io, numpy as np
sys.path.insert(0, "core"); sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image
from dekanat_core import pipeline
from dekanat_core.preprocess.pipeline import map_bbox_back
ref = {d["document_id"]: d for d in json.load(open("data/reference_results.json", encoding="utf-8"))["documents"]}
for did, typ in [("open-002", "study_certificate"), ("open-016", "academic_leave_application"), ("open-030", "internship_certificate")]:
    img = np.asarray(Image.open(f"data/documents/{did}.png").convert("RGB"))
    for k in (1, 2, 3):
        r = np.ascontiguousarray(np.rot90(img, k))
        buf = io.BytesIO(); Image.fromarray(r).save(buf, format="JPEG", quality=85)
        res, ctx = pipeline.process_document(buf.getvalue(), "x.jpg", typ)
        bad = [key for key, v in ref[did]["fields"].items() if res.fields[key].value != v]
        fv = res.fields["student_name"]
        back = map_bbox_back(fv.bbox, ctx.matrix) if fv.bbox else None
        print(did, "rot90 x", k, "steps:", res.quality.get("steps"), "| bad:", bad, "| name bbox on original:", [[int(a) for a in p] for p in back] if back else None, "orig size", r.shape[1::-1])

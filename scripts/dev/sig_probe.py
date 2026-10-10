import sys; sys.path.insert(0, "core"); sys.stdout.reconfigure(encoding="utf-8")
import numpy as np
from PIL import Image
from dekanat_core.ocr import ensemble
from dekanat_core.layout.lines import group_lines
from dekanat_core.marks import detect as md
from dekanat_core.extract.extractor import anchor_bbox
from dekanat_core.config.schema import get_doc_type
for did, typ in [("synth-004","study_certificate"),("synth-005","academic_leave_application"),("synth-011","academic_leave_application"),("synth-001","study_certificate")]:
    rgb = np.asarray(Image.open(f"data/synth/documents/{did}.png").convert("RGB"))
    lines, _ = ensemble.recognize(rgb)
    tl = group_lines(lines)
    spec = [f for f in get_doc_type(typ).mark_fields if f.type=="signature"][0]
    det = md.detect_signature(rgb, tl, spec)
    a = md.find_anchor_line(tl, spec.anchor)
    print(did, det.present, det.details, "| anchor:", a.text if a else None, a.bbox if a else None, anchor_bbox(a, spec.anchor) if a else None)

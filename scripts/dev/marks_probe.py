import sys, json
sys.path.insert(0, "core")
from pathlib import Path
import numpy as np
from PIL import Image
from dekanat_core.ocr import ensemble
from dekanat_core.layout.lines import group_lines
from dekanat_core.marks import detect as md
from dekanat_core.config.schema import get_doc_type
out = open("scripts/dev/marks_probe.txt", "w", encoding="utf-8")
for did, typ in [("open-001","study_certificate"),("open-003","study_certificate"),("open-004","study_certificate"),("open-013","academic_leave_application"),("open-016","academic_leave_application"),("open-030","internship_certificate")]:
    rgb = np.asarray(Image.open(f"data/documents/{did}.png").convert("RGB"))
    lines, _ = ensemble.recognize(rgb)
    tl = group_lines(lines)
    cfg = get_doc_type(typ)
    for spec in cfg.mark_fields:
        det = md.detect_signature(rgb, tl, spec) if spec.type=="signature" else md.detect_seal(rgb, tl, spec)
        anchor = md.find_anchor_line(tl, spec.anchor or "")
        print(did, spec.key, det.present, det.score, det.details, "anchor:", anchor.text if anchor else None, anchor.bbox if anchor else None, file=out, flush=True)

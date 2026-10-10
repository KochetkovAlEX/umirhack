import sys, time, json
sys.path.insert(0, "core")
sys.stdout.reconfigure(encoding="utf-8")
from dekanat_core import pipeline
from pathlib import Path
ref = {d["document_id"]: d for d in json.load(open("data/reference_results.json", encoding="utf-8"))["documents"]}
man = json.load(open("data/documents.json", encoding="utf-8"))
ids = sys.argv[1:] or [m["document_id"] for m in man]
out = open("scripts/dev/run30.txt", "w", encoding="utf-8")
bad = 0; total = 0
for m in man:
    if m["document_id"] not in ids: continue
    t = time.time()
    res, ctx = pipeline.process_document(Path("data", m["image"]).read_bytes(), m["image"], m["document_type"])
    r = ref[m["document_id"]]
    errs = []
    for k, v in r["fields"].items():
        total += 1
        got = res.fields[k].value
        if got != v:
            bad += 1; errs.append(f"  {k}: expected={v!r} got={got!r} raw={res.fields[k].raw!r} conf={res.fields[k].confidence}")
    v_ok = res.validation.status == r["validation"]["status"] and set(res.validation.missing_fields) == set(r["validation"]["missing_fields"]) and set(res.validation.sources) == set(r["validation"]["sources"])
    print(m["document_id"], f"{time.time()-t:.1f}s", "VAL_OK" if v_ok else f"VAL_BAD {res.validation.to_dict()}", res.quality.get("ocr"), file=out, flush=True)
    for e in errs: print(e, file=out, flush=True)
    if errs or not v_ok:
        print("  OCR:", " | ".join(l.text for l in ctx.lines), file=out, flush=True)
print(f"fields bad {bad}/{total}", file=out, flush=True)

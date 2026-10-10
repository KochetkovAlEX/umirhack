import sys, time, numpy as np
from PIL import Image
out = open("scripts/dev/det_probe.txt", "w", encoding="utf-8")
def log(*a): print(*a, file=out, flush=True)
img = np.asarray(Image.open("data/documents/open-002.png").convert("RGB"))[:, :, ::-1].copy()
from paddlex import create_model
for name, kw in [("PP-OCRv5_mobile_det", {}), ("PP-OCRv5_mobile_det", {"cpu_threads": 8}), ("PP-OCRv4_mobile_det", {}), ("PP-OCRv5_server_det", {})]:
    try:
        t = time.time(); m = create_model(model_name=name, enable_mkldnn=False, **kw); log(name, kw, "load", round(time.time()-t,1))
        for i in range(2):
            t = time.time(); res = list(m.predict(img)); log(name, kw, "predict", i, round(time.time()-t,2))
        d = res[0] if isinstance(res[0], dict) else res[0].json["res"]
        polys = d["dt_polys"]; log("n polys", len(polys)); log([[int(v) for v in p[0]] for p in polys][:25])
    except Exception as e:
        log(name, "ERR", repr(e)[:300])

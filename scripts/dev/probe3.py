import os, sys, time, numpy as np
from PIL import Image
out = open("scripts/dev/probe3.txt", "w", encoding="utf-8")
def log(*a): print(*a, file=out, flush=True)
img = np.asarray(Image.open("data/documents/open-002.png").convert("RGB"))[:, :, ::-1].copy()
from paddlex import create_model
det = create_model(model_name="PP-OCRv5_mobile_det", device="cpu", engine_config={"run_mode":"paddle","cpu_threads":8,"enable_new_ir":False})
res = list(det.predict(img)); d = res[0] if isinstance(res[0], dict) else res[0].json["res"]; polys = d["dt_polys"]
crops = []
for p in polys:
    xs=[int(v[0]) for v in p]; ys=[int(v[1]) for v in p]
    crops.append(img[max(0,min(ys)):max(ys), max(0,min(xs)):max(xs)].copy())
for name, ec in [("rec default", None), ("rec mkldnn no_new_ir", {"run_mode":"mkldnn","cpu_threads":8,"enable_new_ir":False}), ("rec paddle new_ir", {"run_mode":"paddle","cpu_threads":8,"enable_new_ir":True})]:
    try:
        kw = {"engine_config": ec} if ec else {}
        t=time.time(); r = create_model(model_name="eslav_PP-OCRv5_mobile_rec", device="cpu", **kw); log(name, "load", round(time.time()-t,1))
        for i in range(2):
            t=time.time(); rr = list(r.predict(crops, batch_size=16)); log(name, "batch", len(crops), round(time.time()-t,2))
        log("  ", [ (x if isinstance(x, dict) else x.json["res"])["rec_text"] for x in rr[-6:]])
    except Exception as e:
        log(name, "ERR", repr(e)[:200])
for name, ec in [("det mkldnn no_new_ir", {"run_mode":"mkldnn","cpu_threads":8,"enable_new_ir":False}), ("det paddle new_ir", {"run_mode":"paddle","cpu_threads":8,"enable_new_ir":True})]:
    try:
        t=time.time(); m = create_model(model_name="PP-OCRv5_mobile_det", device="cpu", engine_config=ec); log(name, "load", round(time.time()-t,1))
        for i in range(2):
            t=time.time(); list(m.predict(img)); log(name, "predict", round(time.time()-t,2))
    except Exception as e:
        log(name, "ERR", repr(e)[:200])

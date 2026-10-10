import os, sys, time, numpy as np
os.environ["FLAGS_use_mkldnn"] = "0"
from PIL import Image
out = open("scripts/dev/det_probe2.txt", "w", encoding="utf-8")
def log(*a): print(*a, file=out, flush=True)
img = np.asarray(Image.open("data/documents/open-002.png").convert("RGB"))[:, :, ::-1].copy()
from paddlex import create_model
from paddlex.inference import PaddlePredictorOption
import inspect
log("PaddlePredictorOption attrs:", [a for a in dir(PaddlePredictorOption) if not a.startswith("_")][:40])
variants = []
opt = PaddlePredictorOption(); 
try: opt.enable_mkldnn = False
except Exception as e: log("set enable_mkldnn err", e)
try: opt.run_mode = "paddle"
except Exception as e: log("set run_mode err", e)
try: opt.cpu_threads = 8
except Exception as e: log("set cpu_threads err", e)
variants.append(("ec", dict(device="cpu", engine_config={"run_mode":"paddle","cpu_threads":8,"enable_new_ir":False})))
for name, kw in variants:
    try:
        t = time.time(); m = create_model(model_name="PP-OCRv5_mobile_det", **kw); log(name, "load", round(time.time()-t,1))
        for i in range(3):
            t = time.time(); res = list(m.predict(img)); log(name, "predict", i, round(time.time()-t,2))
        d = res[0] if isinstance(res[0], dict) else res[0].json["res"]
        polys = d["dt_polys"]; log("n polys", len(polys)); log([[int(v) for v in p[0]] for p in polys][:25])
        # rec timing in batch
        t = time.time(); r = create_model(model_name="eslav_PP-OCRv5_mobile_rec", **kw); log("rec load", round(time.time()-t,1))
        crops = []
        for p in polys:
            xs=[int(v[0]) for v in p]; ys=[int(v[1]) for v in p]
            crops.append(img[max(0,min(ys)):max(ys), max(0,min(xs)):max(xs)].copy())
        t = time.time(); rr = list(r.predict(crops, batch_size=16)); log("rec batch", len(crops), round(time.time()-t,2))
        for x in rr[:30]:
            d = x if isinstance(x, dict) else x.json["res"]; log(repr(d.get("rec_text")), round(float(d.get("rec_score")),3))
    except Exception as e:
        log(name, "ERR", repr(e)[:400])

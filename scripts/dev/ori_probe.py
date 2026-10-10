import sys, time, numpy as np, cv2
sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image
from paddlex import create_model
t=time.time(); m = create_model(model_name="PP-LCNet_x1_0_doc_ori", device="cpu", engine_config={"cpu_threads":8}); print("load", round(time.time()-t,1))
for f in ["data/documents/open-001.png", "data/documents/open-013.png", "bench_out/photo_combo/open-001.png", "data/synth/documents/synth-002.png"]:
    img = np.asarray(Image.open(f).convert("RGB"))[:, :, ::-1].copy()
    for k in (0, 1, 2, 3):
        r = np.ascontiguousarray(np.rot90(img, k))
        t=time.time(); out = list(m.predict(r)); dt=time.time()-t
        d = out[0] if isinstance(out[0], dict) else out[0].json["res"]
        print(f.split('/')[-1], "rot90 x", k, "->", d.get("label_names"), [round(float(s),3) for s in d.get("scores", [])], round(dt,2))

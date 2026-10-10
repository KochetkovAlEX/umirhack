import sys, time, numpy as np
sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image
out = open("scripts/dev/rec_probe.txt", "w", encoding="utf-8")
def log(*a): print(*a, file=out, flush=True)
img = np.asarray(Image.open("data/documents/open-002.png").convert("RGB"))
crop = img[360:395, 100:560]  # строка "ФИО студента: Мельников ..."
Image.fromarray(crop).save("scripts/dev/crop.png")
from paddlex import create_model
for name in ["eslav_PP-OCRv5_mobile_rec", "cyrillic_PP-OCRv3_mobile_rec", "PP-OCRv5_server_rec"]:
    try:
        t = time.time()
        m = create_model(model_name=name, enable_mkldnn=False)
        log(name, "load", round(time.time()-t,1))
        t = time.time()
        for r in m.predict(crop[:, :, ::-1].copy()):
            d = r if isinstance(r, dict) else r.json["res"]
            log(name, "->", repr(d.get("rec_text")), d.get("rec_score"), round(time.time()-t,2))
        # второй прогон для времени
        t = time.time()
        list(m.predict(crop[:, :, ::-1].copy()))
        log(name, "2nd", round(time.time()-t,2))
    except Exception as e:
        log(name, "ERR", repr(e)[:300])

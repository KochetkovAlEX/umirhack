import sys, time, json, os
sys.stdout.reconfigure(encoding="utf-8")
from paddleocr import PaddleOCR
import numpy as np
from PIL import Image
out = open("scripts/dev/ocr_probe.txt", "w", encoding="utf-8")
def log(*a):
    print(*a, file=out, flush=True)
img = np.asarray(Image.open("data/documents/open-002.png").convert("RGB"))
for name, kw in [
    ("mobile_det+ori+threads8", dict(text_detection_model_name="PP-OCRv5_mobile_det", use_textline_orientation=True, cpu_threads=8)),
    ("mobile_det-ori+threads8", dict(text_detection_model_name="PP-OCRv5_mobile_det", use_textline_orientation=False, cpu_threads=8)),
]:
    t = time.time()
    ocr = PaddleOCR(lang="ru", use_doc_orientation_classify=False, use_doc_unwarping=False, enable_mkldnn=False, **kw)
    log(name, "load", round(time.time() - t, 1))
    for i in range(2):
        t = time.time()
        res = ocr.predict(img[:, :, ::-1].copy())
        log(name, "predict", i, round(time.time() - t, 1))
    for r in res:
        d = r if isinstance(r, dict) else r.json["res"]
        for p, tx, s in zip(d["rec_polys"], d["rec_texts"], d["rec_scores"]):
            log(round(float(s), 3), [int(v) for v in p[0]], tx)
# tesseract
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
os.environ["TESSDATA_PREFIX"] = os.path.abspath("models/tessdata")
t = time.time()
txt = pytesseract.image_to_string(img, lang="rus+eng", config="--psm 6")
log("tesseract", round(time.time() - t, 1))
log(txt)

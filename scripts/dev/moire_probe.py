import sys; sys.path.insert(0, "core"); sys.stdout.reconfigure(encoding="utf-8")
import cv2, numpy as np
from PIL import Image
from dekanat_core.ocr import ensemble
from dekanat_core.layout.lines import group_lines
rgb = np.asarray(Image.open("scripts/dev/user_photo2_norm.jpg").convert("RGB"))
gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 12)
print("page ink ratio (noise proxy):", round(float(th.mean()/255), 4))
for name, img in [("raw", rgb), ("median3", cv2.medianBlur(rgb, 3)), ("median5", cv2.medianBlur(rgb, 5)),
                  ("gauss3", cv2.GaussianBlur(rgb, (3, 3), 0)), ("bilateral", cv2.bilateralFilter(rgb, 7, 50, 50)),
                  ("nlmeans", cv2.fastNlMeansDenoisingColored(rgb, None, 7, 7, 7, 21))]:
    lines, _ = ensemble.recognize(np.ascontiguousarray(img))
    tl = group_lines(lines)
    hits = [f"{l.conf:.2f} {l.text}" for l in tl if "студента" in l.text.lower() or "руковод" in l.text.lower()]
    print(name, "|", " || ".join(hits))

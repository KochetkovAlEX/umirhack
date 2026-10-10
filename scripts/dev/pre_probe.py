import sys; sys.path.insert(0, "core"); sys.stdout.reconfigure(encoding="utf-8")
import numpy as np, cv2
from PIL import Image
from dekanat_core.preprocess import pipeline as pre
from dekanat_core.preprocess import quality as q
for name in ["rotate_5", "perspective", "shadow", "photo_combo"]:
    rgb = np.asarray(Image.open(f"bench_out/{name}/open-001.png").convert("RGB"))
    print(name, rgb.shape, q.assess(rgb))
    r = pre.run(rgb)
    print("  steps:", r.steps, "out", r.rgb.shape)
    quad = pre.find_page_quad(rgb)
    print("  quad:", None if quad is None else quad.astype(int).tolist())
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    print("  skew est on raw:", pre.estimate_skew(gray, 30))
    Image.fromarray(r.rgb).save(f"scripts/dev/pre_{name}.png")

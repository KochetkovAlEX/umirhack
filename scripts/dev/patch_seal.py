from pathlib import Path

p = Path(__file__).resolve().parents[2] / "core" / "dekanat_core" / "marks" / "detect.py"
s = p.read_text(encoding="utf-8")
i = s.index("def detect_seal(")
j = s.index("def detect_marks(")
new = '''def _ink_any_color(crop: np.ndarray) -> np.ndarray:
    """Чернила любого цвета: синие (цветная печать) ИЛИ тёмные относительно локального фона
    (чёрно-белая печать, фото с тенями)."""
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    dark = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 12)
    return cv2.bitwise_or(_blue_mask(crop), dark)


def _ring_coverage(mask: np.ndarray, cx: int, cy: int, r: int) -> float:
    ring = np.zeros_like(mask)
    cv2.circle(ring, (int(cx), int(cy)), int(r), 255, max(2, int(r * 0.12)))
    return float((mask & ring).sum() / max(1, ring.sum()))


def detect_seal(rgb: np.ndarray, lines: list[TextLine], spec: FieldSpec) -> MarkDetection:
    cfg = get_settings().get("marks", {}).get("seal", {})
    H, W = rgb.shape[:2]
    anchor = find_anchor_line(lines, spec.anchor or "м.п.", threshold=85)
    if anchor is not None:
        ax1, ay1, ax2, ay2 = anchor_bbox(anchor, spec.anchor or "м.п.")
        cx = (ax1 + ax2) // 2
        r = int(0.14 * W)
        roi = _clip((cx - r, ay1 - 2 * r, cx + r, ay2 + int(0.4 * r)), W, H)
    else:
        roi = _clip((int(W * 0.55), int(H * 0.55), W, int(H * 0.95)), W, H)
    rx1, ry1, rx2, ry2 = roi
    crop = rgb[ry1:ry2, rx1:rx2]
    if crop.size == 0:
        return MarkDetection(False, None, 0.0, {"reason": "empty roi"})
    ink = _ink_any_color(crop)
    # текст (в т.ч. «М.П.» и надписи внутри печати) убираем по OCR-боксам — остаётся кольцо
    for ln in lines:
        lx1, ly1, lx2, ly2 = ln.bbox
        ix1, iy1 = max(lx1, rx1) - rx1, max(ly1, ry1) - ry1
        ix2, iy2 = min(lx2, rx2) - rx1, min(ly2, ry2) - ry1
        if ix2 > ix1 and iy2 > iy1:
            ink[iy1:iy2, ix1:ix2] = 0
    ink = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    ink_ratio = float(ink.mean() / 255)
    min_r = max(8, int(cfg.get("min_radius_ratio", 0.03) * W))
    max_r = max(10, int(cfg.get("max_radius_ratio", 0.12) * W))

    # 1) окружности Хафа на маске чернил
    blur = cv2.GaussianBlur(ink, (9, 9), 2)
    circles = cv2.HoughCircles(blur, cv2.HOUGH_GRADIENT, dp=1.2, minDist=min_r, param1=100, param2=22,
                               minRadius=min_r, maxRadius=max_r)
    best = None
    if circles is not None:
        for cx, cy, r in circles[0][:12]:
            ratio = _ring_coverage(ink, cx, cy, r)
            if best is None or ratio > best[3]:
                best = (int(cx), int(cy), int(r), ratio)

    # 2) запасной признак: крупная компактная кольцевая компонента (округлая выпуклая оболочка, не сплошная)
    blob = None
    closed = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w < 2 * min_r or h < 2 * min_r or not (0.6 < w / max(1, h) < 1.6):
            continue
        hull = cv2.convexHull(cnt)
        area, peri = cv2.contourArea(hull), cv2.arcLength(hull, True)
        if peri <= 0:
            continue
        circularity = 4 * np.pi * area / (peri * peri)
        fill = float(closed[y:y + h, x:x + w].mean() / 255)
        if circularity >= 0.7 and 0.05 < fill < 0.6:
            if blob is None or area > blob[4]:
                blob = (x, y, w, h, area, circularity)

    ok, bbox, score = False, None, 0.0
    min_cov = float(cfg.get("min_ring_coverage", 0.15))
    if best is not None and best[3] >= min_cov:
        cx, cy, r, ratio = best
        ok, score = True, ratio
        bbox = (rx1 + cx - r, ry1 + cy - r, rx1 + cx + r, ry1 + cy + r)
    elif blob is not None:
        x, y, w, h, area, circ = blob
        ok, score = True, float(min(1.0, circ))
        bbox = (rx1 + x, ry1 + y, rx1 + x + w, ry1 + y + h)
    return MarkDetection(ok, bbox, float(score), {"roi": roi, "ink_ratio": round(ink_ratio, 4),
                                                   "circle": round(best[3], 3) if best else None,
                                                   "blob": round(blob[5], 3) if blob else None})


'''
s = s[:i] + new + s[j:]
p.write_text(s, encoding="utf-8")
print("patched")

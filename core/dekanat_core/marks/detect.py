"""Детекция графических отметок: подпись (росчерк) и печать (круглый штамп).

Надписи «Подпись:» и «М.П.» сами по себе отметкой не являются (п. 2.3 Положения):
проверяется наличие графического элемента рядом с якорем.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from ..config.schema import FieldSpec
from ..layout.lines import TextLine
from ..models import BBox, FieldValue
from ..settings import get_settings
from ..extract.extractor import anchor_bbox, find_anchor_line


@dataclass
class MarkDetection:
    present: bool
    bbox: BBox | None
    score: float
    details: dict


def _ink_mask(rgb: np.ndarray) -> np.ndarray:
    """Маска «чернил»: насыщенные (синие/цветные) или достаточно тёмные пиксели."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    colored = (hsv[:, :, 1] > 60) & (hsv[:, :, 2] > 40)
    dark = gray < 110
    return ((colored | dark).astype(np.uint8)) * 255


def _blue_mask(rgb: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    # hue OpenCV 0..180: синий ~ 100..135; допускаем фиолетовый/голубой
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    return (((h >= 90) & (h <= 140) & (s > 50) & (v > 40))).astype(np.uint8) * 255


def _remove_lines(mask: np.ndarray) -> np.ndarray:
    """Убираем горизонтальные линии (линия для подписи) и подчёркивания."""
    w = mask.shape[1]
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (max(15, w // 8), 1))
    horiz = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    horiz = cv2.dilate(horiz, np.ones((3, 3), np.uint8))
    return cv2.bitwise_and(mask, cv2.bitwise_not(horiz))


def _clip(b: BBox, w: int, h: int) -> BBox:
    x1, y1, x2, y2 = b
    return max(0, x1), max(0, y1), min(w, x2), min(h, y2)


def detect_signature(rgb: np.ndarray, lines: list[TextLine], spec: FieldSpec) -> MarkDetection:
    cfg = get_settings().get("marks", {}).get("signature", {})
    H, W = rgb.shape[:2]
    anchor = find_anchor_line(lines, spec.anchor or "подпись")
    if anchor is not None:
        x1, y1, x2, y2 = anchor_bbox(anchor, spec.anchor or "подпись")
        lh = max(10, y2 - y1)
        # зона справа от метки: до ~62% ширины страницы (печать правее), по высоте 1.5 строки вверх и 0.6 вниз
        roi = _clip((x2 + 5, y1 - int(1.5 * lh), min(W, x1 + int(0.62 * W)), y2 + int(0.6 * lh)), W, H)
    else:
        roi = _clip((0, int(H * 0.62), int(W * 0.65), int(H * 0.9)), W, H)
    rx1, ry1, rx2, ry2 = roi
    if rx2 - rx1 < 20 or ry2 - ry1 < 10:
        return MarkDetection(False, None, 0.0, {"reason": "roi too small"})
    crop = rgb[ry1:ry2, rx1:rx2]
    mask = _remove_lines(_ink_mask(crop))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if n <= 1:
        return MarkDetection(False, None, 0.0, {"reason": "no ink", "roi": roi})
    # крупнейшая группа компонентов: объединяем компоненты, близкие друг к другу
    comps = [stats[i] for i in range(1, n) if stats[i][cv2.CC_STAT_AREA] >= 15]
    if not comps:
        return MarkDetection(False, None, 0.0, {"reason": "only noise", "roi": roi})
    comps.sort(key=lambda s: -s[cv2.CC_STAT_AREA])
    big = comps[0]
    bx1, by1 = big[cv2.CC_STAT_LEFT], big[cv2.CC_STAT_TOP]
    bx2, by2 = bx1 + big[cv2.CC_STAT_WIDTH], by1 + big[cv2.CC_STAT_HEIGHT]
    area = int(big[cv2.CC_STAT_AREA])
    for s in comps[1:]:
        sx1, sy1 = s[cv2.CC_STAT_LEFT], s[cv2.CC_STAT_TOP]
        sx2, sy2 = sx1 + s[cv2.CC_STAT_WIDTH], sy1 + s[cv2.CC_STAT_HEIGHT]
        gap = max(sx1 - bx2, bx1 - sx2, 0)
        if gap < 0.03 * W and (min(sy2, by2) - max(sy1, by1)) > -0.02 * H:
            bx1, by1, bx2, by2 = min(bx1, sx1), min(by1, sy1), max(bx2, sx2), max(by2, sy2)
            area += int(s[cv2.CC_STAT_AREA])
    bw, bh = bx2 - bx1, by2 - by1
    roi_h = ry2 - ry1
    ink_ratio = area / max(1, bw * bh)
    # признаки подписи: ширина заметная, высота > четверти ROI, «рыхлость» (не сплошной блок)
    min_h = cfg.get("min_height_ratio", 0.25) * roi_h
    ok = bw > 0.04 * W and bh > min(min_h, 0.6 * roi_h) and bh > 8 and 0.03 < ink_ratio < 0.6 and area > cfg.get(
        "min_ink_ratio", 0.012) * (rx2 - rx1) * roi_h * 0.3
    score = float(min(1.0, (bw / (0.1 * W)) * 0.4 + (bh / max(1, min_h)) * 0.3 + (0.3 if ok else 0)))
    bbox = (rx1 + bx1, ry1 + by1, rx1 + bx2, ry1 + by2) if ok else None
    return MarkDetection(bool(ok), bbox, score, {"roi": roi, "w": int(bw), "h": int(bh), "area": area,
                                                 "ink_ratio": round(float(ink_ratio), 3)})


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
    blue = _blue_mask(crop)
    blue_ratio = float(blue.mean() / 255)
    # ищем окружности на размытой маске
    blur = cv2.GaussianBlur(blue, (9, 9), 2)
    min_r = int(cfg.get("min_radius_ratio", 0.03) * W)
    max_r = int(cfg.get("max_radius_ratio", 0.12) * W)
    circles = cv2.HoughCircles(blur, cv2.HOUGH_GRADIENT, dp=1.2, minDist=min_r, param1=100, param2=25,
                               minRadius=max(8, min_r), maxRadius=max(10, max_r))
    best = None
    if circles is not None:
        for cx, cy, r in circles[0]:
            # доля синих пикселей на кольце
            ring = np.zeros_like(blue)
            cv2.circle(ring, (int(cx), int(cy)), int(r), 255, max(2, int(r * 0.12)))
            ratio = float((blue & ring).sum() / max(1, ring.sum()))
            if best is None or ratio > best[3]:
                best = (int(cx), int(cy), int(r), ratio)
    # альтернативный признак: крупная компактная синяя компонента
    n, labels, stats, _ = cv2.connectedComponentsWithStats(cv2.dilate(blue, np.ones((5, 5), np.uint8)))
    blob = None
    for i in range(1, n):
        w, h = stats[i][cv2.CC_STAT_WIDTH], stats[i][cv2.CC_STAT_HEIGHT]
        if w > 2 * min_r and h > 2 * min_r and 0.6 < w / max(1, h) < 1.6:
            if blob is None or stats[i][cv2.CC_STAT_AREA] > blob[cv2.CC_STAT_AREA]:
                blob = stats[i]
    ok = False
    bbox = None
    score = 0.0
    if best is not None and best[3] >= 0.15:
        cx, cy, r, ratio = best
        ok = True
        score = ratio
        bbox = (rx1 + cx - r, ry1 + cy - r, rx1 + cx + r, ry1 + cy + r)
    elif blob is not None and blue_ratio >= cfg.get("min_blue_ratio", 0.03):
        ok = True
        score = 0.5
        bx, by = blob[cv2.CC_STAT_LEFT], blob[cv2.CC_STAT_TOP]
        bbox = (rx1 + bx, ry1 + by, rx1 + bx + blob[cv2.CC_STAT_WIDTH], ry1 + by + blob[cv2.CC_STAT_HEIGHT])
    return MarkDetection(ok, bbox, float(score), {"roi": roi, "blue_ratio": round(blue_ratio, 4),
                                                   "circle": best[3] if best else None})


def detect_marks(rgb: np.ndarray, lines: list[TextLine], specs: list[FieldSpec]) -> dict[str, FieldValue]:
    out: dict[str, FieldValue] = {}
    for spec in specs:
        det = detect_signature(rgb, lines, spec) if spec.type == "signature" else detect_seal(rgb, lines, spec)
        anchor = find_anchor_line(lines, spec.anchor or spec.label)
        out[spec.key] = FieldValue(
            key=spec.key, label=spec.label, value=bool(det.present), raw="",
            bbox=det.bbox or (anchor.bbox if anchor else None),
            label_bbox=anchor.bbox if anchor else None,
            confidence=round(det.score, 3), found=bool(det.present), kind="mark",
        )
    return out

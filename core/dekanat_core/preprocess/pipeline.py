"""Предобработка «плохих снимков»: перспектива, наклон, тени, блики, апскейл.

Возвращает нормализованное *цветное* изображение (цвет нужен детектору подписи
и печати) и матрицу преобразования исходных координат -> нормализованные.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from ..settings import get_settings
from . import quality as q


@dataclass
class PreprocessResult:
    rgb: np.ndarray                  # нормализованное цветное изображение
    gray_for_ocr: np.ndarray         # улучшенное ч/б для OCR
    matrix: np.ndarray               # 3x3 гомография: исходные -> нормализованные
    steps: list[str] = field(default_factory=list)
    quality: dict = field(default_factory=dict)
    scale: float = 1.0


def _limit_size(rgb: np.ndarray, max_side: int) -> tuple[np.ndarray, float]:
    h, w = rgb.shape[:2]
    s = max(h, w)
    if s <= max_side:
        return rgb, 1.0
    k = max_side / s
    return cv2.resize(rgb, (int(w * k), int(h * k)), interpolation=cv2.INTER_AREA), k


def _scale_matrix(k: float) -> np.ndarray:
    return np.array([[k, 0, 0], [0, k, 0], [0, 0, 1]], dtype=np.float64)


# ---------- перспектива (лист на столе) ----------
def find_page_quad(rgb: np.ndarray) -> np.ndarray | None:
    h, w = rgb.shape[:2]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    # лист светлее фона: порог Оцу + крупнейший контур
    _, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    cnt = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(cnt)
    if area < 0.2 * h * w or area > 0.97 * h * w:
        return None
    peri = cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, 0.03 * peri, True)
    if len(approx) != 4:
        hull = cv2.convexHull(cnt)
        approx = cv2.approxPolyDP(hull, 0.03 * cv2.arcLength(hull, True), True)
        if len(approx) != 4:
            return None
    return approx.reshape(4, 2).astype(np.float32)


def _order_quad(pts: np.ndarray) -> np.ndarray:
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], dtype=np.float32)


def warp_perspective(rgb: np.ndarray, quad: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    tl, tr, br, bl = _order_quad(quad)
    w = int(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl)))
    h = int(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr)))
    if w < 100 or h < 100:
        return rgb, np.eye(3)
    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(np.array([tl, tr, br, bl]), dst)
    return cv2.warpPerspective(rgb, M, (w, h), borderValue=(255, 255, 255)), M


# ---------- наклон ----------
def estimate_skew(gray: np.ndarray, max_angle: float) -> float:
    """Угол наклона текстовых строк в градусах (положительный = против часовой)."""
    small = gray
    if max(gray.shape) > 1500:
        k = 1500 / max(gray.shape)
        small = cv2.resize(gray, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    inv = cv2.bitwise_not(small)
    th = cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    # растягиваем буквы в строки
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (25, 3)))
    edges = cv2.Canny(th, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 360, threshold=80, minLineLength=small.shape[1] // 6, maxLineGap=20)
    if lines is None:
        return 0.0
    angles = []
    weights = []
    for x1, y1, x2, y2 in lines[:, 0]:
        ang = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if abs(ang) <= max_angle:
            angles.append(ang)
            weights.append(np.hypot(x2 - x1, y2 - y1))
    if not angles:
        return 0.0
    angles = np.array(angles)
    weights = np.array(weights)
    # взвешенная медиана
    order = np.argsort(angles)
    cum = np.cumsum(weights[order])
    med = angles[order][np.searchsorted(cum, cum[-1] / 2)]
    return float(med)


def rotate_keep(rgb: np.ndarray, angle: float) -> tuple[np.ndarray, np.ndarray]:
    h, w = rgb.shape[:2]
    c = (w / 2, h / 2)
    R = cv2.getRotationMatrix2D(c, angle, 1.0)
    cos, sin = abs(R[0, 0]), abs(R[0, 1])
    nw, nh = int(h * sin + w * cos), int(h * cos + w * sin)
    R[0, 2] += nw / 2 - c[0]
    R[1, 2] += nh / 2 - c[1]
    out = cv2.warpAffine(rgb, R, (nw, nh), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))
    M = np.vstack([R, [0, 0, 1]])
    return out, M


# ---------- тени / блики ----------
def remove_shadow(rgb: np.ndarray) -> np.ndarray:
    out = []
    for ch in cv2.split(rgb):
        dil = cv2.dilate(ch, np.ones((7, 7), np.uint8))
        bg = cv2.medianBlur(dil, 41)
        diff = 255 - cv2.absdiff(ch, bg)
        norm = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)
        out.append(norm)
    return cv2.merge(out)


def remove_glare(rgb: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    mask = ((hsv[:, :, 2] > 250) & (hsv[:, :, 1] < 20)).astype(np.uint8) * 255
    if mask.mean() < 0.5:  # бликов почти нет
        return rgb
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8))
    return cv2.inpaint(rgb, mask, 3, cv2.INPAINT_TELEA)


# ---------- высота текста ----------
def estimate_text_height(gray: np.ndarray) -> float:
    th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    n, _, stats, _ = cv2.connectedComponentsWithStats(th, connectivity=8)
    hs = stats[1:, cv2.CC_STAT_HEIGHT]
    ws = stats[1:, cv2.CC_STAT_WIDTH]
    ok = (hs > 4) & (hs < gray.shape[0] * 0.05) & (ws < gray.shape[1] * 0.2)
    if ok.sum() < 20:
        return 0.0
    return float(np.median(hs[ok]))


def gray_for_ocr(rgb: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def run(rgb: np.ndarray) -> PreprocessResult:
    cfg = get_settings().get("preprocess", {})
    steps: list[str] = []
    M = np.eye(3)
    rgb, k = _limit_size(rgb, cfg.get("max_side", 2400))
    if k != 1.0:
        M = _scale_matrix(k) @ M
        steps.append(f"resize x{k:.2f}")
    quality = q.assess(rgb)

    if not quality["is_scan_like"]:
        if cfg.get("enable_perspective", True):
            quad = find_page_quad(rgb)
            if quad is not None:
                rgb, Mp = warp_perspective(rgb, quad)
                M = Mp @ M
                steps.append("perspective")
        if cfg.get("enable_glare_removal", True) and quality["glare_ratio"] > 0.002:
            rgb = remove_glare(rgb)
            steps.append("glare")
        if cfg.get("enable_shadow_removal", True) and quality["bg_unevenness"] > 20:
            rgb = remove_shadow(rgb)
            steps.append("shadow")

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    angle = estimate_skew(gray, cfg.get("deskew_max_angle", 30))
    if abs(angle) > 0.3:
        rgb, Mr = rotate_keep(rgb, angle)
        M = Mr @ M
        steps.append(f"deskew {angle:.1f}°")
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    th = estimate_text_height(gray)
    scale = 1.0
    if 0 < th < cfg.get("min_text_height_px", 18):
        scale = 2.0
        rgb = cv2.resize(rgb, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        M = _scale_matrix(2.0) @ M
        steps.append("upscale x2")

    return PreprocessResult(
        rgb=rgb, gray_for_ocr=gray_for_ocr(rgb), matrix=M, steps=steps, quality=quality, scale=scale
    )


def map_bbox_back(bbox, M: np.ndarray):
    """bbox нормализованного изображения -> 4 точки на исходном снимке."""
    x1, y1, x2, y2 = bbox
    pts = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.float64)
    Minv = np.linalg.inv(M)
    hom = np.hstack([pts, np.ones((4, 1))]) @ Minv.T
    hom /= hom[:, 2:3]
    return [[float(x), float(y)] for x, y in hom[:, :2]]

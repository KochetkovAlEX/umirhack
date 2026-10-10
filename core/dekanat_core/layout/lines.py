"""Сборка OCR-боксов в визуальные строки и разбор «Метка: значение»."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..models import BBox, OcrLine


@dataclass
class TextLine:
    text: str
    bbox: BBox
    conf: float
    parts: list[OcrLine] = field(default_factory=list)

    @property
    def height(self) -> int:
        return self.bbox[3] - self.bbox[1]

    @property
    def cy(self) -> float:
        return (self.bbox[1] + self.bbox[3]) / 2


def _union(a: BBox, b: BBox) -> BBox:
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def group_lines(ocr: list[OcrLine]) -> list[TextLine]:
    """Боксы с пересечением по вертикали > 50% высоты объединяются в строку."""
    items = sorted(ocr, key=lambda l: ((l.bbox[1] + l.bbox[3]) / 2, l.bbox[0]))
    rows: list[list[OcrLine]] = []
    for it in items:
        cy = (it.bbox[1] + it.bbox[3]) / 2
        h = max(1, it.bbox[3] - it.bbox[1])
        placed = False
        for row in rows:
            ry1 = min(r.bbox[1] for r in row)
            ry2 = max(r.bbox[3] for r in row)
            rh = max(1, ry2 - ry1)
            overlap = min(it.bbox[3], ry2) - max(it.bbox[1], ry1)
            if overlap > 0.5 * min(h, rh) and abs(cy - (ry1 + ry2) / 2) < 0.7 * max(h, rh):
                row.append(it)
                placed = True
                break
        if not placed:
            rows.append([it])
    out: list[TextLine] = []
    for row in rows:
        row.sort(key=lambda l: l.bbox[0])
        bbox = row[0].bbox
        for r in row[1:]:
            bbox = _union(bbox, r.bbox)
        text = " ".join(r.text.strip() for r in row)
        conf = sum(r.conf for r in row) / len(row)
        out.append(TextLine(text=re.sub(r"\s+", " ", text).strip(), bbox=bbox, conf=conf, parts=row))
    out.sort(key=lambda l: (l.bbox[1], l.bbox[0]))
    return out


_SEP_RE = re.compile(r"\s*[:：]\s*")


def split_label_value(line: TextLine) -> tuple[str, str, BBox | None, BBox | None]:
    """Вернуть (метка, значение, bbox метки, bbox значения).

    bbox значения оценивается по частям OCR, лежащим правее двоеточия; если
    двоеточие внутри одного бокса — доля ширины по символам.
    """
    text = line.text
    m = _SEP_RE.search(text)
    if not m:
        return text, "", line.bbox, None
    label = text[: m.start()].strip()
    value = text[m.end():].strip()

    # bbox: ищем часть, содержащую двоеточие
    label_bbox: BBox | None = None
    value_bbox: BBox | None = None
    acc = 0
    for part in line.parts:
        ptext = part.text.strip()
        start, end = acc, acc + len(ptext)
        acc = end + 1
        if start <= m.start() < end + 1:
            # разделитель внутри этой части
            frac = (m.end() - start) / max(1, len(ptext))
            x1, y1, x2, y2 = part.bbox
            xs = x1 + int((x2 - x1) * min(1.0, frac))
            label_bbox = (x1, y1, xs, y2) if label_bbox is None else _union(label_bbox, (x1, y1, xs, y2))
            if frac < 0.98:
                value_bbox = (xs, y1, x2, y2)
        elif end <= m.start():
            label_bbox = part.bbox if label_bbox is None else _union(label_bbox, part.bbox)
        else:
            value_bbox = part.bbox if value_bbox is None else _union(value_bbox, part.bbox)
    return label, value, label_bbox or line.bbox, value_bbox


def full_text(lines: list[TextLine]) -> str:
    return "\n".join(l.text for l in lines)

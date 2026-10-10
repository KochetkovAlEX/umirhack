#!/usr/bin/env python
"""Вставить таблицу из bench_report.json в README между маркерами BENCH_TABLE_START/END."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
report = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "bench_report.json")
rows = json.loads(report.read_text(encoding="utf-8"))
n = sys.argv[2] if len(sys.argv) > 2 else "?"
lines = [f"Аугментации открытого набора ({n} документов на вариант), метрики `evaluate.py` + точность автоопределения типа и отметок:", "",
         "| Аугментация | Поля | Проверка | Вопросы | Тип (авто) | Подпись/печать | с/док |", "|---|---|---|---|---|---|---|"]
for r in rows:
    lines.append(f"| {r['aug']} | {r['fields']:.3f} | {r['validation']:.3f} | {r['questions']:.3f} | {r['type_acc']:.3f} | {r['marks_acc']:.3f} | {r['sec_per_doc']} |")
readme = ROOT / "README.md"
text = readme.read_text(encoding="utf-8")
start, end = "<!-- BENCH_TABLE_START -->", "<!-- BENCH_TABLE_END -->"
i, j = text.index(start) + len(start), text.index(end)
readme.write_text(text[:i] + "\n" + "\n".join(lines) + "\n" + text[j:], encoding="utf-8")
print("README обновлён")

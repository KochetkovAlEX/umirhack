import os, sys, json, django
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "../core"); sys.path.insert(0, "."); os.environ["DJANGO_SETTINGS_MODULE"] = "dekanat.settings"; os.environ["DEKANAT_WARMUP"] = "0"
django.setup()
from django.test import Client
c = Client()
print("health", c.get("/api/v1/health").json())
print("types", [t["key"] for t in c.get("/api/v1/doc-types").json()])
print("rules", c.get("/api/v1/rules").json()["sections"][0]["title"])
with open("../data/documents/open-002.png", "rb") as f:
    r = c.post("/api/v1/documents", {"file": f, "doc_type": "auto", "question": "Какова дата выдачи?"})
print("upload", r.status_code)
d = r.json(); did = d["id"]
print("type", d["doc_type"], d["type_confidence"], "status", d["status"], "val", d["result"]["validation"]["status"], d["result"]["validation"]["missing_fields"])
print("answer", d["answer"])
print("fields", {k: v["value"] for k, v in d["result"]["fields"].items()})
for q in ["Содержит ли документ все обязательные сведения?", "Кто принимает решение?", "Какой размер стипендии?", "Укажи значение поля «ФИО студента»."]:
    a = c.post(f"/api/v1/documents/{did}/ask", json.dumps({"question": q}), content_type="application/json").json()
    print(" ask:", q, "->", a["answerable"], a["value"], a["sources"], "|", a["answer"][:90])
print("check", c.post(f"/api/v1/documents/{did}/check").json()["value"])
print("boxes", len(c.get(f"/api/v1/documents/{did}/boxes").json()))
print("annotated", c.get(f"/api/v1/documents/{did}/annotated.png").status_code, "crop", c.get(f"/api/v1/documents/{did}/fields/student_name/crop.png").status_code, "crop seal", c.get(f"/api/v1/documents/{did}/fields/seal_present/crop.png").status_code)
print("image", c.get(f"/api/v1/documents/{did}/image?variant=original").status_code, c.get(f"/api/v1/documents/{did}/image?variant=normalized").status_code)
r = c.patch(f"/api/v1/documents/{did}", json.dumps({"doc_type": "internship_certificate"}), content_type="application/json")
print("retype", r.status_code, r.json()["doc_type"], r.json()["result"]["validation"]["status"], len(r.json()["result"]["validation"]["missing_fields"]))
print("export", json.dumps(c.get(f"/api/v1/documents/{did}/export.json").json(), ensure_ascii=False)[:200])
with open("../data/documents/open-013.pdf", "rb") as f:
    r = c.post("/api/v1/documents", {"file": f, "doc_type": "academic_leave_application", "check": "true"})
print("pdf upload", r.status_code, r.json()["answer"]["value"], r.json()["answer"]["answer"][:100])
r = c.post("/api/v1/documents", {"file": open("../README.md" if os.path.exists("../README.md") else "../data/rules.md", "rb")})
print("bad file", r.status_code, r.json())
print("schema", c.get("/api/schema/").status_code, "swagger", c.get("/api/docs/").status_code, "spa", c.get("/").status_code)

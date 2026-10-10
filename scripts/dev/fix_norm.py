p = "core/dekanat_core/extract/normalizers.py"
s = open(p, encoding="utf-8").read()
i = s.index("def normalize_text"); j = s.index("def normalize(", i)
new = '''def normalize_text(raw: str) -> str:
    s = normalize_quotes(clean_spaces(raw)).strip(" .")
    # OCR склеивает кавычку со словом и теряет закрывающую: «организация«Спектр» -> «организация «Спектр»»
    s = re.sub(r"(\w)«", r"\1 «", s)
    s = re.sub(r"»(\w)", r"» \1", s)
    if s.count("«") > s.count("»"):
        s = s + "»"
    if s.count("»") > s.count("«"):
        # потеряна открывающая кавычка: «организацияСпектр»» -> «организация «Спектр»»
        s2 = re.sub(r"([а-яёa-z])([А-ЯЁA-Z][^»]*»)", r"\1 «\2", s, count=1)
        s = s2 if s2 != s else re.sub(r"(\s|^)([^\s»]+»)", r"\1«\2", s, count=1)
    return clean_spaces(s)


'''
s = s[:i] + new + s[j:]
open(p, "w", encoding="utf-8").write(s)
print("fixed")

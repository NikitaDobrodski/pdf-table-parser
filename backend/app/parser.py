import io
import re
import unicodedata
from typing import Any, Dict, List, Optional
import pdfplumber

# Нормализация текста в ячейке: удаление неразрывных пробелов, замена переносов строк на пробелы, удаление лишних пробелов
def _norm_cell(x: Any) -> str:
    if x is None:
        return ""
    s = str(x)
    s = s.replace("\u00a0", " ")
    s = s.replace("\r", "\n")
    s = re.sub(r"[ \t]*\n[ \t]*", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

# Извлечение таблиц из PDF с помощью pdfplumber, поддержка указания страниц и ограничения количества таблиц
def extract_tables_pdfplumber(
    pdf_bytes: bytes,
    pages: Optional[str] = None,
    max_tables: int = 2000,
) -> List[Dict[str, Any]]:

    out: List[Dict[str, Any]] = []

    table_settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 3,
        "join_tolerance": 3,
        "edge_min_length": 20,
        "intersection_tolerance": 5,
        "text_tolerance": 2,
        "min_words_vertical": 1,
        "min_words_horizontal": 1,
    }

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        total = len(pdf.pages)
        page_nums = _parse_pages_1based(pages, total)  # сделай как у тебя уже было

        for pno in page_nums:
            page = pdf.pages[pno - 1]
            tables = page.find_tables(table_settings=table_settings)

            for ti, tbl in enumerate(tables):
                raw = tbl.extract() or []
                rows = [[_norm_cell(c) for c in r] for r in raw]
                rows = [r for r in rows if any(c for c in r)]
                if not rows:
                    continue

                out.append({"page": pno, "table_index": ti, "rows": rows})
                if len(out) >= max_tables:
                    return out

    return out

# Нормализация текста в ячейке: удаление неразрывных пробелов, замена переносов строк на пробелы, удаление лишних пробелов
def _norm_cell(x) -> str:
    if x is None:
        return ""
    s = str(x)
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u00a0", " ")
    s = s.replace("\r", "\n")
    s = re.sub(r"[ \t]*\n[ \t]*", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    return s
# Парсинг строк формата страниц, поддержка форматов: "all", "1", "1-3", "1,3,5-7"
def _parse_pages_1based(pages: Optional[str], total_pages: int) -> List[int]:
    if pages is None or pages.strip() == "" or pages.strip().lower() == "all":
        return list(range(1, total_pages + 1))

    s = pages.strip().lower()
    if not re.fullmatch(r"[0-9,\-\s]+", s):
        raise ValueError("Invalid pages format")

    result = set()
    for part in [p.strip() for p in s.split(",") if p.strip()]:
        if "-" in part:
            a, b = [x.strip() for x in part.split("-", 1)]
            a, b = int(a), int(b)
            if a > b:
                a, b = b, a
            for x in range(a, b + 1):
                if 1 <= x <= total_pages:
                    result.add(x)
        else:
            x = int(part)
            if 1 <= x <= total_pages:
                result.add(x)

    if not result:
        raise ValueError("Pages out of range")
    return sorted(result)
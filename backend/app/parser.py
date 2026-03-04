import io
import re
from typing import List, Optional, Tuple

import pdfplumber


def parse_pages(pages: Optional[str], total_pages: int) -> List[int]:
    """
    pages:
      None / "all" -> все страницы
      "1" -> [1]
      "1-3" -> [1,2,3]
      "1,3,5-7" -> [1,3,5,6,7]
    Возвращает 1-based номера страниц.
    """
    if not pages or pages.strip().lower() == "all":
        return list(range(1, total_pages + 1))

    s = pages.replace(" ", "")
    if not re.fullmatch(r"[0-9,\-]+", s):
        raise ValueError("pages must be like '1', '1-3', '1,3,5-7' or 'all'")

    result = set()
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-", 1)
            if not a or not b:
                raise ValueError("bad pages range")
            start = int(a)
            end = int(b)
            if start > end:
                start, end = end, start
            for p in range(start, end + 1):
                result.add(p)
        else:
            result.add(int(part))

    # ограничим диапазоном реального PDF
    filtered = [p for p in sorted(result) if 1 <= p <= total_pages]
    if not filtered:
        raise ValueError("pages out of range")
    return filtered


def extract_tables_pdfplumber(
    pdf_bytes: bytes,
    pages: Optional[str] = None,
    max_tables: int = 200,
):
    results = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        page_list = parse_pages(pages, total_pages=len(pdf.pages))

        for page_i in page_list:
            page = pdf.pages[page_i - 1]
            tables = page.extract_tables() or []

            for t_i, rows in enumerate(tables):
                norm_rows = [
                    [("" if c is None else str(c)) for c in row]
                    for row in (rows or [])
                ]
                results.append({
                    "page": page_i,
                    "table_index": t_i,
                    "rows": norm_rows
                })

                if len(results) >= max_tables:
                    return results

    return results
from __future__ import annotations
import csv
import io
import re
import zipfile
from typing import List, Optional, Tuple
from ..grouping import TableGroupItem, group_tables_by_header

_NUM_RE = re.compile(r"^\d{1,4}$")
_CODE_RE = re.compile(r"^\d{3,4}$")
_SECTION_RE = re.compile(r"^\s*(.+?\(Код\s*[0-9A-Z]{2,4}XX\))\s*$", re.IGNORECASE)
_ATA_RE = re.compile(r"\bATA\s*([0-9]{2}-[0-9]{2}-[0-9]{2})\b", re.IGNORECASE)


def _pad_rows(rows: List[List[str]], width: int) -> List[List[str]]:
    out = []
    for r in rows:
        rr = list(r)
        if len(rr) < width:
            rr.extend([""] * (width - len(rr)))
        out.append(rr)
    return out


def _is_data_row(row: List[str]) -> bool:
    c1 = (row[0] if len(row) > 0 else "").strip()
    c2 = (row[1] if len(row) > 1 else "").strip()
    return bool(_NUM_RE.match(c1) and _CODE_RE.match(c2))


def _extract_context_from_row(row: List[str]) -> Tuple[Optional[str], Optional[str]]:
    parts = [c.strip() for c in row if c and c.strip()]
    if not parts:
        return None, None

    text = " ".join(parts)
    text = re.sub(r"\s+", " ", text).strip()

    section = None
    ata = None

    m_ata = _ATA_RE.search(text)
    if m_ata:
        ata = m_ata.group(1)

    m_sec = _SECTION_RE.match(text)
    if m_sec:
        section = m_sec.group(1).strip()
    else:
        if len(text) >= 20 and not _is_data_row(row):
            section = text

    return section, ata


def merge_wrapped_rows_by_first_col(rows: List[List[str]]) -> List[List[str]]:
    out: List[List[str]] = []
    for r in rows:
        if not out:
            out.append(r)
            continue

        first = (r[0] if len(r) > 0 else "").strip()
        if first == "" or not _NUM_RE.match(first):
            prev = out[-1]
            width = max(len(prev), len(r))
            if len(prev) < width:
                prev.extend([""] * (width - len(prev)))
            if len(r) < width:
                r = r + [""] * (width - len(r))

            for i in range(width):
                if r[i]:
                    prev[i] = (prev[i] + " " + r[i]).strip() if prev[i] else r[i]
        else:
            out.append(r)
    return out


def build_grouped_csv_zip(
    tables: List[dict],
    delimiter: str = ";",
    base_prefix: str = "tables",
    include_meta: bool = False,
    include_context: bool = True,   # <-- новое
) -> bytes:
    if delimiter not in (",", ";"):
        raise ValueError("csv_delim must be ',' or ';'")

    grouped = group_tables_by_header(
        tables,
        drop_noise_rows=False,       # <-- важно: НЕ выкидываем контекстные строки
        attach_continuations=True,
    )

    bio = io.BytesIO()
    with zipfile.ZipFile(bio, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        group_no = 0
        for sig, items in grouped.items():
            if not items:
                continue

            group_no += 1
            safe_name = f"group_{group_no:03d}"
            if sig:
                preview = "_".join([c[:20] for c in sig[:2] if c]).strip("_")
                if preview:
                    safe_name += f"__{preview}"

            csv_text = _group_to_csv_text(
                items,
                delimiter=delimiter,
                include_meta=include_meta,
                include_context=include_context,
            )
            zf.writestr(f"{base_prefix}/{safe_name}.csv", csv_text.encode("utf-8"))

    return bio.getvalue()


def _group_to_csv_text(
    items: List[TableGroupItem],
    delimiter: str,
    include_meta: bool,
    include_context: bool,
) -> str:
    sio = io.StringIO(newline="")
    w = csv.writer(
        sio,
        delimiter=delimiter,
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\n",
    )

    header = items[0].header if items and items[0].header else []
    data_width = max((len(r) for it in items for r in it.rows), default=0)
    width = max(len(header), data_width)
    meta_cols = ["page", "table_index"] if include_meta else []
    ctx_cols = ["Section", "ATA"] if include_context else []

    if header:
        w.writerow(ctx_cols + meta_cols + _pad_rows([header], width)[0])

    current_section: Optional[str] = None
    current_ata: Optional[str] = None

    for it in items:
        rows = merge_wrapped_rows_by_first_col(it.rows)
        rows = _pad_rows(rows, width)

        for r in rows:
            sec, ata = _extract_context_from_row(r)
            if sec:
                current_section = sec
                continue
            if ata:
                current_ata = ata
                continue
            if not _is_data_row(r):
                continue

            prefix = []
            if include_context:
                prefix.extend([current_section or "", current_ata or ""])
            if include_meta:
                prefix.extend([it.ref.page, it.ref.table_index])

            w.writerow(prefix + r)

    return sio.getvalue()
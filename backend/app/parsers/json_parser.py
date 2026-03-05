from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ..grouping import group_tables_by_header


def build_grouped_json_payload(
    tables: List[dict],
    filename: str,
    pages: str,
) -> Dict[str, Any]:
    """
    JSON пайплайн:
      - группировка по заголовкам
      - отдаёт структурированный JSON по группам
    """
    grouped = group_tables_by_header(tables, drop_noise_rows=True)

    groups = []
    group_no = 0
    for sig, items in grouped.items():
        group_no += 1
        groups.append({
            "group_index": group_no,
            "signature": list(sig),
            "tables": [
                {
                    "page": it.ref.page,
                    "table_index": it.ref.table_index,
                    "header": it.header,
                    "rows": it.rows,
                }
                for it in items
            ],
        })

    return {
        "filename": filename,
        "pages": pages,
        "groups_count": len(groups),
        "groups": groups,
    }
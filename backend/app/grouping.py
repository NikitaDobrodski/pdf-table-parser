from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# Структуры для представления ссылок на таблицы и группированных таблиц с общими заголовками
@dataclass(frozen=True)
class TableRef:
    page: int
    table_index: int

# Структура для хранения информации о группе таблиц с общими заголовками
@dataclass
class TableGroupItem:
    ref: TableRef
    header: List[str]
    rows: List[List[str]]
    sig: Tuple[str, ...]

# Нормализация текста: удаление неразрывных пробелов, замена переносов строк на пробелы, удаление лишних пробелов
def _norm_text(s: str) -> str:
    s = (s or "").replace("\u00a0", " ")
    s = s.replace("\r", "\n").replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

# Нормализация строки таблицы: применение нормализации к каждой ячейке
def normalize_row(row: List[str]) -> List[str]:
    return [_norm_text(c) for c in (row or [])]

# Проверка, является ли строка таблицы полностью пустой (все ячейки пустые после нормализации)
def is_row_empty(row: List[str]) -> bool:
    return all((_norm_text(c) == "") for c in (row or []))

# Проверка, является ли строка с одним непустым элементом шумовой (например, заголовок продолжения таблицы, номер страницы и т.п.)
def is_noise_single_cell_row(text: str) -> bool:
    t = _norm_text(text).lower()
    if not t:
        return True
    noise_prefixes = (
        "таблица",
        "продолжение",
        "рисунок",
        "лист",
        "стр.",
        "страница",
        "раздел",
        "глава",
        "приложение",
        "каталог алгоритмов",
    )
    if any(t.startswith(p) for p in noise_prefixes):
        return True
    if re.fullmatch(r"[\d\.\-\(\) ]+", t):
        return True
    return False

# Определение максимального количества столбцов в строках таблицы, чтобы понять структуру данных
def _best_colcount(rows: List[List[str]]) -> int:
    return max((len(r) for r in rows), default=0)

# Проверка, выглядит ли строка как строка данных из каталога алгоритмов (например, содержит номер, код и наименование)
def looks_like_catalog_data_row(row: List[str]) -> bool:
    r = normalize_row(row)
    if len(r) < 3:
        return False
    c1, c2, c3 = r[0], r[1], r[2]
    if not re.fullmatch(r"\d{1,4}", c1 or ""):
        return False
    if not re.fullmatch(r"\d{3,4}", c2 or ""):
        return False
    if len((c3 or "").strip()) < 3:
        return False
    return True

# Генерация стандартного заголовка для таблицы на основе количества столбцов, если явного заголовка не найдено
def default_header_for_colcount(colcount: int) -> List[str]:
    if colcount <= 0:
        return []
    if colcount == 5:
        return ["№", "Код", "Наименование", "Условие", "Параметры"]
    if colcount == 6:
        return ["№", "Код", "Наименование", "Условие", "Параметры", "Примечание/Документ"]
    if colcount == 7:
        return ["№", "Код", "Наименование", "Условие", "Параметры", "Примечание/Документ", "Доп."]
    return [f"Col{idx}" for idx in range(1, colcount + 1)]

# Определение индекса строки, которая может быть заголовком таблицы, основываясь на количестве непустых ячеек и их содержимом
def detect_header_row(rows: List[List[str]]) -> Optional[int]:
    for i, r in enumerate(rows):
        rr = normalize_row(r)
        non_empty = [c for c in rr if c]
        if not non_empty:
            continue
        if len(non_empty) == 1 and is_noise_single_cell_row(non_empty[0]):
            continue

        if looks_like_catalog_data_row(rr):
            continue

        if len(non_empty) >= 2:
            return i
    return None

# Создание сигнатуры заголовка для группировки таблиц: нормализовать заголовок и удалить пустые ячейки в конце
def header_signature(header: List[str]) -> Tuple[str, ...]:
    h = normalize_row(header)
    while h and h[-1] == "":
        h.pop()
    return tuple(h)

# Группировка таблиц по их заголовкам: для каждой таблицы определить заголовок, создать сигнатуру и сгруппировать таблицы с одинаковой сигнатурой вместе. Также обрабатывать случаи, когда заголовок не найден, и пытаться прикрепить такие таблицы к последнему найденному заголовку с таким же количеством столбцов.
def group_tables_by_header(
    tables: List[Dict[str, Any]],
    drop_noise_rows: bool = True,
    attach_continuations: bool = True,
) -> Dict[Tuple[str, ...], List[TableGroupItem]]:
    grouped: Dict[Tuple[str, ...], List[TableGroupItem]] = {}

    last_by_colcount: Dict[int, Tuple[Tuple[str, ...], List[str]]] = {}

    for t in tables:
        page = int(t.get("page", 0) or 0)
        table_index = int(t.get("table_index", 0) or 0)
        raw_rows = t.get("rows") or []

        rows = [normalize_row(r) for r in raw_rows if r is not None]
        rows = [r for r in rows if not is_row_empty(r)]

        if drop_noise_rows:
            cleaned = []
            for r in rows:
                non_empty = [c for c in r if c]
                if len(non_empty) == 1 and is_noise_single_cell_row(non_empty[0]):
                    continue
                cleaned.append(r)
            rows = cleaned

        if not rows:
            continue

        colcount = _best_colcount(rows)
        header_i = detect_header_row(rows)

        if header_i is None:
            data_rows = rows

            if attach_continuations and colcount in last_by_colcount:
                sig, header = last_by_colcount[colcount]
            else:
                header = default_header_for_colcount(colcount)
                sig = tuple(header)

            item = TableGroupItem(
                ref=TableRef(page=page, table_index=table_index),
                header=header,
                rows=data_rows,
                sig=sig,
            )
            grouped.setdefault(sig, []).append(item)

            if sig:
                last_by_colcount[colcount] = (sig, header)
            continue

        header_row = rows[header_i]
        data_rows = rows[header_i + 1 :]

        sig = header_signature(header_row)
        if not sig:
            header = default_header_for_colcount(colcount)
            sig = tuple(header)
        else:
            header = list(sig)

        item = TableGroupItem(
            ref=TableRef(page=page, table_index=table_index),
            header=header,
            rows=data_rows,
            sig=sig,
        )
        grouped.setdefault(sig, []).append(item)

        if sig:
            last_by_colcount[colcount] = (sig, header)

    return grouped
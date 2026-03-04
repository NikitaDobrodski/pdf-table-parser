cd D:\Work\PythonScripts\pdf-table-parser

@'
# PDF Table Parser (pdf-table-parser)

Сервис на **FastAPI**, который извлекает таблицы из PDF и возвращает результат в **JSON / CSV / XLSX**.

> Примечание: на Windows порт **8000** иногда бывает занят/запрещён (WinError 10013), поэтому по умолчанию используем **8010**.

---

## Структура проекта

```text
pdf-table-parser/
├─ backend/
│  ├─ app/
│  │  ├─ main.py        # FastAPI API
│  │  ├─ parser.py      # извлечение таблиц из PDF
│  │  └─ exporters.py   # экспорт XLSX (openpyxl)
│  ├─ requirements.txt
│  └─ Dockerfile
└─ docker-compose.yml

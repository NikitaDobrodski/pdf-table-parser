# PDF Table Parser (pdf-table-parser)

Сервис на **FastAPI**, который извлекает таблицы из PDF и возвращает результат в **JSON / CSV / XLSX**.

> На Windows порт **8000** иногда бывает занят/запрещён (WinError 10013), поэтому по умолчанию используем **8010**.

---

## Структура проекта

```text
pdf-table-parser/
├─ backend/
│  ├─ app/
│  │  ├─ __init__.py
│  │  ├─ main.py        # FastAPI API
│  │  ├─ parser.py      # извлечение таблиц из PDF
│  │  └─ exporters.py   # экспорт XLSX (openpyxl)
│  ├─ requirements.txt
│  └─ Dockerfile
└─ docker-compose.yml
Запуск локально (Windows, через .venv)

Перейди в корень проекта (папку репозитория):

cd <папка_репозитория>

Установи зависимости в текущий venv:

.\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt

Запусти сервер:

.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8010

Swagger (документация):

http://127.0.0.1:8010/docs

Проверка:

http://127.0.0.1:8010/health

Запуск в Docker

Сборка и запуск:

docker compose up --build

После запуска:

http://127.0.0.1:8010/docs

Остановка:

docker compose down
Использование API
POST /parse

Параметры:

pages — какие страницы парсить: 1, 1-3, 1,3,5-7, all (по умолчанию все)

format — json | csv | xlsx (по умолчанию json)

max_tables — ограничение на количество таблиц (защита), по умолчанию 200

Примеры (PowerShell):

JSON
curl -X POST "http://127.0.0.1:8010/parse?pages=7-93&format=json&max_tables=200" `
  -H "accept: application/json" `
  -H "Content-Type: multipart/form-data" `
  -F "file=@.\path\to\file.pdf"
CSV (скачивание в файл)
curl -X POST "http://127.0.0.1:8010/parse?pages=7-93&format=csv&max_tables=200" `
  -H "Content-Type: multipart/form-data" `
  -F "file=@.\path\to\file.pdf" `
  -o result.csv
XLSX (скачивание в файл)
curl -X POST "http://127.0.0.1:8010/parse?pages=7-93&format=xlsx&max_tables=5000" `
  -H "Content-Type: multipart/form-data" `
  -F "file=@.\path\to\file.pdf" `
  -o result.xlsx

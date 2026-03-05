from __future__ import annotations
from urllib.parse import quote
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse, Response
from .parser import extract_tables_pdfplumber
from .parsers.csv_parser import build_grouped_csv_zip
from .parsers.xlsx_parser import build_grouped_xlsx
from .parsers.json_parser import build_grouped_json_payload

app = FastAPI(title="PDF Table Parser", version="0.2.0")

# Для имен файлов в Content-Disposition нужно обеспечить ASCII-совместимость, чтобы избежать проблем с разными браузерами и кодировками.
def _ascii_fallback_filename(name: str) -> str:
    safe = []
    for ch in name:
        o = ord(ch)
        if 32 <= o < 127 and ch not in ['"', "\\"]:
            safe.append(ch)
        else:
            safe.append("_")
    res = "".join(safe).strip()
    return res or "download"

# Content-Disposition с поддержкой UTF-8 и ASCII-резервом для старых браузеров. Формат: attachment; filename="fallback.txt"; filename*=UTF-8''encoded.txt
def _content_disposition(filename: str) -> str:
    fallback = _ascii_fallback_filename(filename)
    quoted = quote(filename, safe="")
    return f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{quoted}'

# Эндпоинт для проверки работоспособности сервера
@app.get("/health")
def health():
    return {"status": "ok"}

# Основной эндпоинт для загрузки PDF и получения распарсенных таблиц в нужном формате
@app.post("/parse")
async def parse(
    file: UploadFile = File(...),
    pages: str = Form(
        "all",
        description="Какие страницы парсить: all | 1 | 1-3 | 1,3,5-7",
        examples=["all", "1", "1-3", "1,3,5-7"],
    ),
    format: str = Form("json", pattern=r"^(json|csv|xlsx)$"),
    max_tables: int = Form(2000, ge=1, le=5000),
    csv_delim: str = Form(";", pattern=r"^(,|;)$"),
):
    try:
        pdf_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")

    try:
        tables = extract_tables_pdfplumber(pdf_bytes, pages=pages, max_tables=max_tables)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parse error: {e}")

    base_name = (file.filename or "document.pdf").rsplit(".", 1)[0]

    if format == "json":
        payload = build_grouped_json_payload(
            tables=tables,
            filename=file.filename or "document.pdf",
            pages=pages or "all",
        )
        return JSONResponse(payload)

    if format == "csv":
        zip_bytes = build_grouped_csv_zip(
            tables=tables,
            delimiter=csv_delim,
            base_prefix=base_name,
        )
        out_name = f"{base_name}_groups.zip"
        headers = {
            "Content-Disposition": _content_disposition(out_name),
            "Content-Type": "application/zip",
        }
        return Response(content=zip_bytes, headers=headers, media_type="application/zip")

    if format == "xlsx":
        xlsx_bytes = build_grouped_xlsx(
            tables=tables,
            base_title=base_name,
        )
        out_name = f"{base_name}_groups.xlsx"
        headers = {
            "Content-Disposition": _content_disposition(out_name),
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        return Response(content=xlsx_bytes, headers=headers, media_type=headers["Content-Type"])

    raise HTTPException(status_code=400, detail="Unknown format")
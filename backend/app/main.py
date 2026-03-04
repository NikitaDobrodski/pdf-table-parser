import re
import urllib.parse

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse, Response

from .parser import extract_tables_pdfplumber
from .exporters import tables_to_xlsx_bytes

app = FastAPI(title="PDF Table Parser")


def _ascii_fallback_filename(name: str, default: str = "result") -> str:
    """
    Делает безопасное ASCII-имя: убирает всё кроме латиницы/цифр/._-
    """
    name = (name or "").strip()
    if not name:
        name = default
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^A-Za-z0-9._-]", "", name)
    return name or default


def _content_disposition(filename: str) -> str:
    """
    Content-Disposition:
      - filename="..." (ASCII fallback, чтобы Starlette не падал на latin-1)
      - filename*=UTF-8''... (RFC 5987, чтобы браузер сохранил кириллицу)
    """
    ascii_name = _ascii_fallback_filename(filename)
    quoted_utf8 = urllib.parse.quote(filename, safe="")
    return f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{quoted_utf8}'


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/parse")
async def parse_pdf(
    file: UploadFile = File(...),
    pages: str | None = Query(
        default=None,
        description="e.g. '1', '1-3', '1,3,5-7', or 'all'"
    ),
    format: str = Query(
        default="json",
        pattern="^(json|csv|xlsx)$",
        description="Response format"
    ),
    max_tables: int = Query(
        default=200,
        ge=1,
        le=5000,
        description="Safety limit: max number of tables to return"
    ),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Upload a .pdf file")

    pdf_bytes = await file.read()

    try:
        tables = extract_tables_pdfplumber(pdf_bytes, pages=pages, max_tables=max_tables)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parse failed: {e}")

    # ---- JSON ----
    if format == "json":
        return JSONResponse(content={
            "filename": file.filename,
            "pages": pages or "all",
            "tables_count": len(tables),
            "tables": tables
        })

    base = file.filename.rsplit(".", 1)[0]
    suffix = (pages or "all").replace(",", "_").replace("-", "_")

    # ---- CSV ----
    if format == "csv":
        lines = []
        for t in tables:
            lines.append(f"# page={t['page']} table={t['table_index']}")
            for row in t["rows"]:
                # простейший CSV: экранируем кавычки
                esc = [f"\"{c.replace('\"', '\"\"')}\"" for c in row]
                lines.append(",".join(esc))
            lines.append("")

        csv_text = "\n".join(lines)
        fname = f"{base}_{suffix}.csv"

        return Response(
            content=csv_text.encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": _content_disposition(fname)}
        )

    # ---- XLSX ----
    xlsx_bytes = tables_to_xlsx_bytes(tables)
    fname = f"{base}_{suffix}.xlsx"

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": _content_disposition(fname)}
    )
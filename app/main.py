"""FastAPI web application for Mindbox → SFMC conversion."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.blocks import ConversionParams
from app.converter import convert_mindbox_to_sfmc
from app.validator import ValidationReport, validate_sfmc_html

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "cxq_mapping.json"

app = FastAPI(title="Mindbox → SFMC Converter", version="1.0.0")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def load_cxq_data() -> dict:
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return {"rows": [], "brands": [], "unique_values": {}}


def report_to_dict(report: ValidationReport) -> dict:
    return {
        "ok": report.ok,
        "issues": [
            {
                "block": issue.block,
                "severity": issue.severity,
                "message": issue.message,
                "hint": issue.hint,
                "snippet": issue.snippet,
            }
            for issue in report.issues
        ],
    }


def is_mindbox_filename(name: str) -> bool:
    return "mindbox" in name.lower()


def build_output_name(filename: str) -> str:
    stem = Path(filename).stem
    if "mindbox" in stem.lower():
        new_stem = stem.replace("Mindbox", "SFMC").replace("mindbox", "SFMC")
        if new_stem == stem:
            new_stem = f"{stem}_SFMC"
    else:
        new_stem = f"{stem}_SFMC"
    return f"{new_stem}.html"


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    cxq = load_cxq_data()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "cxq": cxq,
        },
    )


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})

async def cxq_data() -> JSONResponse:
    return JSONResponse(load_cxq_data())


@app.post("/api/validate")
async def validate_only(file: UploadFile = File(...)) -> JSONResponse:
    content = (await file.read()).decode("utf-8", errors="replace")
    report = validate_sfmc_html(
        content,
        is_mindbox_source=is_mindbox_filename(file.filename or ""),
    )
    return JSONResponse(report_to_dict(report))


@app.post("/api/convert")
async def convert(
    file: UploadFile = File(...),
    data_extension: str = Form("Akamai_profiles_consents_bounced"),
    personalization_mode: str = Form("de"),
    privacy_url: str = Form(""),
    utm_campaign: str = Form(""),
    cxq_brand: str = Form(""),
    cxq_da: str = Form(""),
    cxq_ta: str = Form(""),
    cxq_bu: str = Form("GENERAL MEDICINES"),
    cxq_function: str = Form("Commercial"),
    cxq_cn: str = Form("journey"),
) -> JSONResponse:
    content = (await file.read()).decode("utf-8", errors="replace")
    params = ConversionParams(
        data_extension=data_extension.strip(),
        personalization_mode=personalization_mode.strip(),
        privacy_url=privacy_url.strip(),
        utm_campaign=utm_campaign.strip(),
        cxq_brand=cxq_brand.strip(),
        cxq_da=cxq_da.strip(),
        cxq_ta=cxq_ta.strip(),
        cxq_bu=cxq_bu.strip(),
        cxq_function=cxq_function.strip(),
        cxq_cn=cxq_cn.strip(),
    )

    before_report = validate_sfmc_html(
        content,
        is_mindbox_source=is_mindbox_filename(file.filename or ""),
    )
    result = convert_mindbox_to_sfmc(content, params)
    after_report = validate_sfmc_html(result.html)

    return JSONResponse(
        {
            "html": result.html,
            "output_filename": build_output_name(file.filename or "email.html"),
            "changes": result.changes,
            "warnings": result.warnings,
            "validation_before": report_to_dict(before_report),
            "validation_after": report_to_dict(after_report),
        }
    )


@app.post("/api/download")
async def download(
    file: UploadFile = File(...),
    data_extension: str = Form("Akamai_profiles_consents_bounced"),
    personalization_mode: str = Form("de"),
    privacy_url: str = Form(""),
    utm_campaign: str = Form(""),
    cxq_brand: str = Form(""),
    cxq_da: str = Form(""),
    cxq_ta: str = Form(""),
    cxq_bu: str = Form("GENERAL MEDICINES"),
    cxq_function: str = Form("Commercial"),
    cxq_cn: str = Form("journey"),
) -> Response:
    content = (await file.read()).decode("utf-8", errors="replace")
    params = ConversionParams(
        data_extension=data_extension.strip(),
        personalization_mode=personalization_mode.strip(),
        privacy_url=privacy_url.strip(),
        utm_campaign=utm_campaign.strip(),
        cxq_brand=cxq_brand.strip(),
        cxq_da=cxq_da.strip(),
        cxq_ta=cxq_ta.strip(),
        cxq_bu=cxq_bu.strip(),
        cxq_function=cxq_function.strip(),
        cxq_cn=cxq_cn.strip(),
    )
    result = convert_mindbox_to_sfmc(content, params)
    filename = build_output_name(file.filename or "email.html")
    return Response(
        content=result.html,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

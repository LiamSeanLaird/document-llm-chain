import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.db import (
    get_or_create_kpi,
    init_db,
    insert_kpi_value,
    insert_report,
    insert_section,
    list_kpi_values,
    list_reports,
    list_sections,
)
from app.logging_config import configure_logging
from app.pipeline.classify import classify_sections
from app.pipeline.extract import extract_to_xml, garbage_char_frequency
from app.pipeline.kpi_definitions import GHG_KPIS
from app.pipeline.kpis import extract_kpi_values
from app.storage import resolve_report_path, save_upload

configure_logging()
logger = logging.getLogger("pipeline")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    for kpi in GHG_KPIS:
        get_or_create_kpi(kpi["id"], kpi["name"], kpi["description"])
    yield


app = FastAPI(title="Document LLM Chain", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ReportRequest(BaseModel):
    reportUrl: str


@app.post("/uploads")
async def upload_report(file: UploadFile = File(...)):
    content = await file.read()
    report_url = save_upload(file.filename, content)
    return {"reportUrl": report_url}


@app.post("/reports")
async def process_report(payload: ReportRequest):
    pdf_path = resolve_report_path(payload.reportUrl)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="report not found")
    return StreamingResponse(_run_pipeline(payload.reportUrl, pdf_path), media_type="text/event-stream")


@app.get("/list_reports")
def get_reports():
    return list_reports()


@app.get("/list_sections")
def get_sections(report_id: str | None = None):
    return list_sections(report_id)


@app.get("/list_kpi_values")
def get_kpi_values():
    return list_kpi_values()


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _run_pipeline(report_url: str, pdf_path: Path):
    report_id = uuid.uuid4().hex
    logger.info("=== processing report %s (%s) ===", report_id, report_url)

    yield _sse("stage_started", {"stage": 1, "name": "extract"})
    t0 = time.monotonic()
    xml = extract_to_xml(pdf_path)
    garbage_ratio = garbage_char_frequency(xml)
    check = "PASS" if garbage_ratio < 0.02 else "FAIL"
    logger.info(
        "stage 1 extract: %d XML chars, garbage_char_frequency=%.4f (%s, threshold 0.02) [%.2fs]",
        len(xml),
        garbage_ratio,
        check,
        time.monotonic() - t0,
    )
    insert_report(report_id, report_url, xml)
    yield _sse("stage_completed", {"stage": 1, "name": "extract", "xml_chars": len(xml)})

    yield _sse("stage_started", {"stage": 2, "name": "classify"})
    t0 = time.monotonic()
    sections = classify_sections(xml)
    for section in sections:
        section_id = uuid.uuid4().hex
        section["id"] = section_id
        insert_section(section_id, report_id, section["text"], section["sort"], section["topics"])
    logger.info("stage 2 classify: %d sections persisted [%.2fs]", len(sections), time.monotonic() - t0)
    yield _sse("stage_completed", {"stage": 2, "name": "classify", "section_count": len(sections)})

    yield _sse("stage_started", {"stage": 3, "name": "extract_kpi_values"})
    t0 = time.monotonic()
    kpi_values = extract_kpi_values(sections)
    for kpi_value in kpi_values:
        insert_kpi_value(
            uuid.uuid4().hex,
            kpi_value["kpi_id"],
            kpi_value["section"]["id"],
            kpi_value["value"],
            kpi_value["period"],
        )
    logger.info(
        "stage 3 extract_kpi_values: %d values persisted [%.2fs]", len(kpi_values), time.monotonic() - t0
    )
    yield _sse(
        "stage_completed", {"stage": 3, "name": "extract_kpi_values", "value_count": len(kpi_values)}
    )

    logger.info("=== finished report %s ===", report_id)
    yield _sse("done", {"reportId": report_id})

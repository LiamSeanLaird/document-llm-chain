import uuid
from pathlib import Path

from app.config import REPORTS_DIR


def save_upload(filename: str, content: bytes) -> str:
    """Store an uploaded report locally and return its reportUrl.

    Stands in for an S3 pre-signed-upload flow: the caller gets back an
    opaque reportUrl, not a filesystem path, so this can be swapped for a
    real object store later without changing callers.
    """
    suffix = Path(filename).suffix or ".pdf"
    report_id = uuid.uuid4().hex
    dest = REPORTS_DIR / f"{report_id}{suffix}"
    dest.write_bytes(content)
    return f"local://{dest.name}"


def resolve_report_path(report_url: str) -> Path:
    if not report_url.startswith("local://"):
        raise ValueError(f"unsupported reportUrl scheme: {report_url}")
    return REPORTS_DIR / report_url.removeprefix("local://")

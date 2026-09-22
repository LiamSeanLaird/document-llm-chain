import json
import sqlite3
from contextlib import contextmanager

from app.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS report (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    xml TEXT
);

CREATE TABLE IF NOT EXISTS section (
    id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL REFERENCES report(id),
    text TEXT NOT NULL,
    sort INTEGER NOT NULL,
    topics TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS kpi (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS kpi_value (
    id TEXT PRIMARY KEY,
    kpi_id TEXT NOT NULL REFERENCES kpi(id),
    section_id TEXT NOT NULL REFERENCES section(id),
    value TEXT NOT NULL,
    period TEXT NOT NULL
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def insert_report(report_id: str, url: str, xml: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO report (id, url, xml) VALUES (?, ?, ?)",
            (report_id, url, xml),
        )


def insert_section(section_id: str, report_id: str, text: str, sort: int, topics: list[str]) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO section (id, report_id, text, sort, topics) VALUES (?, ?, ?, ?, ?)",
            (section_id, report_id, text, sort, json.dumps(topics)),
        )


def get_or_create_kpi(kpi_id: str, name: str, description: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO kpi (id, name, description) VALUES (?, ?, ?)",
            (kpi_id, name, description),
        )


def insert_kpi_value(value_id: str, kpi_id: str, section_id: str, value: str, period: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO kpi_value (id, kpi_id, section_id, value, period) VALUES (?, ?, ?, ?, ?)",
            (value_id, kpi_id, section_id, value, period),
        )


def list_reports() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT id, url, xml FROM report ORDER BY rowid").fetchall()
        return [dict(row) for row in rows]


def list_sections(report_id: str | None = None) -> list[dict]:
    with get_conn() as conn:
        if report_id:
            rows = conn.execute(
                "SELECT id, report_id, text, sort, topics FROM section WHERE report_id = ? ORDER BY sort",
                (report_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, report_id, text, sort, topics FROM section ORDER BY report_id, sort"
            ).fetchall()
        sections = []
        for row in rows:
            section = dict(row)
            section["topics"] = json.loads(section["topics"])
            sections.append(section)
        return sections


def list_kpi_values() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                kpi_value.id AS id,
                kpi.name AS kpi_name,
                kpi_value.value AS value,
                kpi_value.period AS period,
                kpi_value.section_id AS section_id,
                section.report_id AS report_id
            FROM kpi_value
            JOIN kpi ON kpi.id = kpi_value.kpi_id
            JOIN section ON section.id = kpi_value.section_id
            ORDER BY kpi_value.rowid
            """
        ).fetchall()
        return [dict(row) for row in rows]

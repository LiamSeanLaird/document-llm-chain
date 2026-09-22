"""Stage 1: parse a report PDF into XML, tagging headers, paragraphs, and tables."""

import statistics
import xml.etree.ElementTree as ET
from pathlib import Path

import pdfplumber

HEADER_SIZE_RATIO = 1.15


def _word_in_any_bbox(word: dict, bboxes: list[tuple]) -> bool:
    x0, top, x1, bottom = word["x0"], word["top"], word["x1"], word["bottom"]
    for bx0, btop, bx1, bbottom in bboxes:
        if x0 >= bx0 - 1 and x1 <= bx1 + 1 and top >= btop - 1 and bottom <= bbottom + 1:
            return True
    return False


def _group_words_into_lines(words: list[dict], y_tolerance: float = 3) -> list[list[dict]]:
    lines: list[list[dict]] = []
    current_line: list[dict] = []
    current_top: float | None = None
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if current_top is None or abs(word["top"] - current_top) <= y_tolerance:
            current_line.append(word)
            current_top = word["top"] if current_top is None else current_top
        else:
            lines.append(current_line)
            current_line = [word]
            current_top = word["top"]
    if current_line:
        lines.append(current_line)
    return lines


def _extract_page_elements(page) -> list[dict]:
    tables = page.find_tables()
    table_bboxes = [t.bbox for t in tables]

    words = page.extract_words(extra_attrs=["size"])
    text_words = [w for w in words if not _word_in_any_bbox(w, table_bboxes)]
    lines = _group_words_into_lines(text_words)

    line_sizes = [statistics.mean(w["size"] for w in line) for line in lines]
    median_size = statistics.median(line_sizes) if line_sizes else 0

    elements: list[dict] = []
    paragraph_buffer: list[str] = []

    def flush_paragraph():
        if paragraph_buffer:
            elements.append({"type": "paragraph", "text": " ".join(paragraph_buffer)})
            paragraph_buffer.clear()

    for line, size in zip(lines, line_sizes):
        text = " ".join(w["text"] for w in sorted(line, key=lambda w: w["x0"]))
        if median_size and size >= median_size * HEADER_SIZE_RATIO:
            flush_paragraph()
            elements.append({"type": "header", "text": text})
        else:
            paragraph_buffer.append(text)
    flush_paragraph()

    for table in tables:
        rows = table.extract() or []
        elements.append({"type": "table", "rows": rows})

    return elements


def extract_to_xml(pdf_path: str | Path) -> str:
    root = ET.Element("report")
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            page_el = ET.SubElement(root, "page", number=str(page_number))
            for element in _extract_page_elements(page):
                if element["type"] == "table":
                    table_el = ET.SubElement(page_el, "table")
                    for row in element["rows"]:
                        row_el = ET.SubElement(table_el, "row")
                        for cell in row:
                            cell_el = ET.SubElement(row_el, "cell")
                            cell_el.text = cell or ""
                else:
                    el = ET.SubElement(page_el, element["type"])
                    el.text = element["text"]
    ET.indent(root)
    return ET.tostring(root, encoding="unicode")


def garbage_char_frequency(text: str) -> float:
    """Fraction of characters that are neither printable ASCII nor common punctuation/whitespace.

    Used to catch PDF-extraction artifacts such as encoding mangling or broken ligatures.
    """
    if not text:
        return 0.0
    allowed = set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        " \t\n\r.,;:!?()[]{}'\"-_/%$€£@#&*+=<>|\\~`^"
    )
    garbage = sum(1 for ch in text if ch not in allowed and not ch.isspace())
    return garbage / len(text)

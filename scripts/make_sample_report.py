"""Generate a synthetic sustainability report PDF for manually exercising the pipeline.

Usage: python scripts/make_sample_report.py [out_path]
"""

import sys
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def make_sample_report(pdf_path: Path) -> None:
    c = canvas.Canvas(str(pdf_path), pagesize=letter)

    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, 740, "Acme Corp Sustainability Report 2023")

    c.setFont("Helvetica", 11)
    c.drawString(72, 710, "This report discloses Acme Corp's greenhouse gas emissions")
    c.drawString(72, 695, "for the 2023 fiscal year, broken down by scope.")

    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 660, "Scope 1 and Scope 2 Emissions")

    c.setFont("Helvetica", 11)
    c.drawString(72, 635, "Scope 1 emissions totaled 1,250 tCO2e in FY2023.")
    c.drawString(72, 618, "Scope 2 emissions (location-based) totaled 3,400 tCO2e in FY2023.")

    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 580, "Scope 3 Emissions")

    c.setFont("Helvetica", 11)
    c.drawString(72, 555, "Scope 3 emissions totaled 18,900 tCO2e in FY2023, primarily from")
    c.drawString(72, 538, "purchased goods and services and business travel.")

    table_x = 72
    table_top_y = 500
    row_height = 20
    col_width = 120
    rows = [
        ["Scope", "Value (tCO2e)"],
        ["Scope 1", "1250"],
        ["Scope 2", "3400"],
        ["Scope 3", "18900"],
    ]

    for row_index in range(len(rows) + 1):
        y = table_top_y - row_index * row_height
        c.line(table_x, y, table_x + 2 * col_width, y)
    for col_index in range(3):
        x = table_x + col_index * col_width
        c.line(x, table_top_y, x, table_top_y - len(rows) * row_height)

    c.setFont("Helvetica", 10)
    for row_index, row in enumerate(rows):
        y = table_top_y - row_index * row_height - 14
        for col_index, cell in enumerate(row):
            x = table_x + col_index * col_width + 5
            c.drawString(x, y, cell)

    c.showPage()
    c.save()


if __name__ == "__main__":
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("sample_report.pdf")
    make_sample_report(out_path)
    print(f"wrote {out_path}")

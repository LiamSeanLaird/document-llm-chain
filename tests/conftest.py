import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


@pytest.fixture
def sample_pdf_path(tmp_path):
    """A small synthetic sustainability report: a header, a paragraph, and a bordered table."""
    pdf_path = tmp_path / "sample_report.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)

    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, 740, "GHG Emissions Summary")

    c.setFont("Helvetica", 11)
    c.drawString(72, 710, "This report discloses the company's greenhouse gas emissions")
    c.drawString(72, 695, "for the 2023 fiscal year, broken down by scope.")

    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 660, "Scope 1 and Scope 2 Emissions")

    c.setFont("Helvetica", 11)
    c.drawString(72, 635, "Scope 1 emissions totaled 1,250 tCO2e in FY2023.")

    table_x = 72
    table_top_y = 600
    row_height = 20
    col_width = 100
    rows = [["Scope", "Value (tCO2e)"], ["Scope 1", "1250"], ["Scope 2", "3400"]]

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
    return pdf_path

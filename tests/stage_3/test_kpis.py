import os

import pytest

from app.pipeline.kpis import extract_kpi_values

pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"), reason="requires OPENAI_API_KEY to call OpenAI"
)

SAMPLE_SECTIONS = [
    {
        "id": "section-1",
        "text": "Scope 1 emissions totaled 1,250 tCO2e in FY2023.",
        "topics": ["ghg_emissions"],
        "sort": 0,
    }
]


def test_extract_kpi_values_returns_validated_scope_1_value():
    values = extract_kpi_values(SAMPLE_SECTIONS)

    assert len(values) == 1
    assert values[0]["kpi_name"] == "Scope 1 Emissions"
    assert values[0]["period"] == "FY2023"

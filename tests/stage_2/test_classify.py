import os

import pytest

from app.pipeline.classify import classify_sections

pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"), reason="requires OPENAI_API_KEY to call OpenAI"
)

SAMPLE_XML = (
    "<report><page number=\"1\">"
    "<header>Scope 1 and Scope 2 Emissions</header>"
    "<paragraph>Scope 1 emissions totaled 1,250 tCO2e in FY2023.</paragraph>"
    "</page></report>"
)


def test_classify_sections_assigns_topics():
    sections = classify_sections(SAMPLE_XML)

    assert len(sections) >= 1
    assert all(section["topics"] for section in sections)
    assert any("ghg_emissions" in section["topics"] for section in sections)

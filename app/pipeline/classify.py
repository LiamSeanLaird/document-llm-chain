"""Stage 2: chunk the extracted XML into logical sections and assign topics."""

import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.config import EXTRACTION_MODEL
from app.pipeline.schemas import SectionsOutput

logger = logging.getLogger(__name__)

MAX_SECTION_WORDS = 500

CLASSIFY_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You split a sustainability report, given as XML with header/paragraph/table "
            "elements, into logically coherent sections. Preserve the original text "
            "verbatim inside each section - do not summarize or paraphrase. Assign each "
            "section one or more topics from this set when they apply: ghg_emissions, "
            "energy, water, waste, governance, social, other.",
        ),
        ("human", "{report_xml}"),
    ]
)


def classify_sections(report_xml: str) -> list[dict]:
    model = ChatOpenAI(model=EXTRACTION_MODEL, temperature=0)
    chain = CLASSIFY_PROMPT | model.with_structured_output(SectionsOutput)
    result: SectionsOutput = chain.invoke({"report_xml": report_xml})
    sections = [
        {"text": section.text, "topics": section.topics, "sort": index}
        for index, section in enumerate(result.sections)
    ]

    logger.info("stage 2 classify: produced %d section(s)", len(sections))
    for section in sections:
        word_count = len(section["text"].split())
        check = "within bound" if word_count <= MAX_SECTION_WORDS else "OVER BOUND"
        logger.info(
            "  section %d: %d words (%s, threshold %d), topics=%s",
            section["sort"],
            word_count,
            check,
            MAX_SECTION_WORDS,
            section["topics"],
        )

    return sections

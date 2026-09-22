"""Stage 3: extract candidate KPI values from classified sections, then verify each one
with a second model call before it's returned for persistence."""

import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.config import EXTRACTION_MODEL, VALIDATION_MODEL
from app.pipeline.kpi_definitions import GHG_KPIS
from app.pipeline.schemas import KpiExtractionsOutput, KpiValidation

logger = logging.getLogger(__name__)

RELEVANT_TOPICS = {"ghg_emissions"}

EXTRACT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You extract greenhouse gas emissions KPI values from a section of a "
            "sustainability report. Only extract values for these KPIs:\n{kpi_list}\n"
            "Only extract a value if it is explicitly stated in the section text. "
            "If none of the KPIs are present, return an empty list.",
        ),
        ("human", "{section_text}"),
    ]
)

VALIDATE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You check whether an extracted KPI value correctly maps to its stated KPI "
            "and reporting period, based on the section text it was extracted from. Flag "
            "as invalid anything with the wrong unit, wrong order of magnitude, or a "
            "period that doesn't match the source text.",
        ),
        (
            "human",
            "Section text:\n{section_text}\n\n"
            "Extracted KPI: {kpi_name}\nValue: {value} {unit}\nPeriod: {period}",
        ),
    ]
)


def _kpi_list_text() -> str:
    return "\n".join(f"- {kpi['name']}: {kpi['description']}" for kpi in GHG_KPIS)


def _kpi_name_to_id() -> dict[str, str]:
    return {kpi["name"]: kpi["id"] for kpi in GHG_KPIS}


def extract_kpi_values(sections: list[dict]) -> list[dict]:
    """Extract and validate KPI values from classified sections.

    Only values that pass the second-model validation check are returned - nothing
    unvalidated is handed back for persistence.
    """
    extraction_model = ChatOpenAI(model=EXTRACTION_MODEL, temperature=0)
    extraction_chain = EXTRACT_PROMPT | extraction_model.with_structured_output(KpiExtractionsOutput)

    validation_model = ChatOpenAI(model=VALIDATION_MODEL, temperature=0)
    validation_chain = VALIDATE_PROMPT | validation_model.with_structured_output(KpiValidation)

    kpi_ids = _kpi_name_to_id()
    kpi_list_text = _kpi_list_text()
    validated_values = []

    relevant_sections = [s for s in sections if RELEVANT_TOPICS.intersection(s["topics"])]
    logger.info(
        "stage 3 extract_kpi_values: %d/%d section(s) tagged with a relevant topic",
        len(relevant_sections),
        len(sections),
    )

    for section in relevant_sections:
        logger.info("  scanning section %s (topics=%s)", section.get("id", section["sort"]), section["topics"])

        extraction_result: KpiExtractionsOutput = extraction_chain.invoke(
            {"kpi_list": kpi_list_text, "section_text": section["text"]}
        )
        logger.info("    found %d candidate KPI value(s)", len(extraction_result.extractions))

        for extraction in extraction_result.extractions:
            kpi_id = kpi_ids.get(extraction.kpi_name)
            if kpi_id is None:
                logger.warning("    skipping unrecognized KPI name from model: %r", extraction.kpi_name)
                continue

            validation_result: KpiValidation = validation_chain.invoke(
                {
                    "section_text": section["text"],
                    "kpi_name": extraction.kpi_name,
                    "value": extraction.value,
                    "unit": extraction.unit,
                    "period": extraction.period,
                }
            )
            outcome = "ACCEPTED" if validation_result.is_valid else "REJECTED"
            logger.info(
                "    %s %s = %s %s (%s): %s",
                outcome,
                extraction.kpi_name,
                extraction.value,
                extraction.unit,
                extraction.period,
                validation_result.reason,
            )
            if not validation_result.is_valid:
                continue

            validated_values.append(
                {
                    "kpi_id": kpi_id,
                    "kpi_name": extraction.kpi_name,
                    "section": section,
                    "value": f"{extraction.value} {extraction.unit}",
                    "period": extraction.period,
                }
            )

    logger.info("stage 3 extract_kpi_values: %d value(s) validated and ready to persist", len(validated_values))
    return validated_values

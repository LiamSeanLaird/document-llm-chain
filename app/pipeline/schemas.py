from pydantic import BaseModel, Field


class SectionOutput(BaseModel):
    text: str = Field(description="The section's source text, copied verbatim from the input.")
    topics: list[str] = Field(
        description="One or more topic tags for this section, e.g. 'ghg_emissions', 'energy', 'water', 'governance', 'other'."
    )


class SectionsOutput(BaseModel):
    sections: list[SectionOutput]


class KpiExtraction(BaseModel):
    kpi_name: str = Field(description="Name of the matched KPI, must match one of the provided KPI names exactly.")
    value: str = Field(description="The extracted numeric value, as text, e.g. '12345.6'.")
    unit: str = Field(description="The unit of the value, e.g. 'tCO2e'.")
    period: str = Field(description="The reporting period the value applies to, e.g. 'FY2023'.")


class KpiExtractionsOutput(BaseModel):
    extractions: list[KpiExtraction]


class KpiValidation(BaseModel):
    is_valid: bool = Field(description="Whether the extracted value correctly maps to the stated KPI and period.")
    reason: str = Field(description="Short justification for the validation decision.")

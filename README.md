# Document LLM Chain

A practice project for learning multi-stage LLM document-processing pipelines with LangChain.

## What this project is

This is a three-stage LLM chain that extracts greenhouse gas (GHG) emissions KPIs from a corporate sustainability report (PDF) into structured, traceable records suitable for an ESG dataset.
The concrete example: given a sustainability report, find Scope 1, Scope 2, and Scope 3 emissions figures, along with their units and reporting periods, and store them so each value can be traced back to the exact report section it came from.

The pipeline exists to practice designing and implementing an LLM chain where each stage is independently testable and gates progress to the next stage, not to build a production ESG platform.
Scalability and distributed-systems concerns are explicitly out of scope.
The focus is the algorithmic process inside each stage and the end-to-end latency of running a report through the chain.

The design was scoped out before implementation started: three stages, four core entities, no multi-company modeling, no distributed infrastructure.

## Pipeline stages

1. **Extract structure.** Parse the report PDF into XML, capturing headers, paragraphs, tables, and figures as structured, positioned content.
   Text is grouped by detected column band before line-grouping, and words inside an embedded chart/illustration's bounding box are pulled into a separate `<figure>` element rather than being classified as headers or paragraphs - real multi-column sustainability reports otherwise splice unrelated columns' sentences together and misread chart data-point labels as section headers.
   Tests: XML tags open and close correctly, garbage-character frequency stays under 2%.
2. **Classify sections.** Use an LLM to chunk the extracted XML into logical sections and assign each one a topic.
   Tests: section size stays under a defined word count, and assigned topics match a labeled fixture set.
3. **Extract and validate KPI values.** Loop through classified sections, identify relevant GHG KPIs, and capture their values, units, and periods.
   A second model call checks, within the same stage, that each captured value maps correctly to its KPI and period before anything is persisted.
   Tests: the second model's mapping check is run against a labeled fixture set of known-good and known-bad extractions.

Each stage has its own test suite that must pass before the next stage is wired in.
Stage 1's tests check that the extraction code is correct in general, using fixture PDFs, not that any single report was extracted correctly at runtime.

## Architecture

- **Client to server.** A FastAPI server exposes the pipeline over HTTP, with Server-Sent Events (SSE) streaming stage-by-stage progress back to the client as a report is processed.
- **Server to storage.** Uploaded reports are written to local filesystem storage rather than S3, since this project isn't testing cloud infrastructure.
  The storage layer is abstracted behind the same interface a real pre-signed-URL flow would use, so it can be swapped for S3 later without touching the pipeline stages.
- **Server to DB.** SQLite holds reports, sections, KPIs, and KPI values.
  SQLite is used instead of Postgres for the same reason as local storage: no external services to run for a single-user practice project.

- **Server to client (dev UI).** A minimal Next.js page in `web/` uploads a report, consumes the SSE stream live, and renders the persisted reports, sections, and KPI values in tabbed tables.
  It talks to the FastAPI server over plain HTTP/CORS, not through Next's own server - there's no backend-for-frontend layer here.

### API

- `POST /uploads` - accepts a report file (multipart), stores it in local storage, returns a `reportUrl`.
- `POST /reports` - body `{ "reportUrl": "..." }`, kicks off the three-stage pipeline for that report, streams progress via SSE.
- `GET /list_reports` - returns persisted reports, including their extracted XML.
- `GET /list_sections` - returns persisted sections; optional `?report_id=` filters to one report.
- `GET /list_kpi_values` - returns extracted KPI values for display in a table.

Detailed per-stage output - extraction stats, each section's word count against its threshold, each KPI candidate's validation outcome and reason - is not sent over SSE.
It's logged to the FastAPI server's own console as the pipeline runs, so you can watch the pipeline's internal reasoning in the terminal running `uvicorn` while the UI shows only stage-level progress.

## Data model

| Entity | Fields |
| --- | --- |
| Report | `url`, `xml` |
| Section | `reportId`, `text`, `sort`, `topics` |
| Kpi | `name`, `description` |
| KpiValue | `kpiId`, `sectionId`, `value`, `period` |

`KpiValue.sectionId` is what makes results traceable: every displayed value points back to the exact section, and its text, that it was extracted from.

There is no `Company` entity.
The design assumes a single company per report and doesn't validate KPI values against external company context.

## Repo layout

```
document-llm-chain/
├── README.md
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml        # pytest config only, not a package build config
├── .env.example
├── app/
│   ├── main.py            # FastAPI app, routes, SSE pipeline runner
│   ├── config.py          # env vars, data dir paths
│   ├── db.py               # SQLite schema + DAO functions
│   ├── storage.py          # local filesystem storage abstraction
│   ├── logging_config.py   # server-side stage/test logging setup
│   └── pipeline/
│       ├── kpi_definitions.py  # predefined GHG KPI list
│       ├── schemas.py          # pydantic schemas for LLM structured output
│       ├── extract.py          # stage 1: PDF -> XML
│       ├── classify.py         # stage 2: chunk + topic assignment
│       └── kpis.py             # stage 3: extract + validate KPI values
├── scripts/
│   └── make_sample_report.py   # generates a synthetic report PDF for manual testing
├── tests/
│   ├── conftest.py        # synthetic PDF fixture (reportlab)
│   ├── stage_1/           # runs offline, no API key needed
│   ├── stage_2/           # skipped unless OPENAI_API_KEY is set
│   └── stage_3/           # skipped unless OPENAI_API_KEY is set
├── web/                   # minimal Next.js dev UI (see "Web UI" below)
└── data/                  # local storage + sqlite db (gitignored)
```

## Terminology

- **GHG KPI** - a greenhouse gas emissions metric, e.g. Scope 1, Scope 2, or Scope 3 emissions in tCO2e.
- **Scope 1/2/3** - GHG Protocol categories: Scope 1 is direct emissions, Scope 2 is purchased energy, Scope 3 is everything else in the value chain.
- **Section** - a logically coherent chunk of a report, assigned one or more topics by stage 2.
- **Stage gate** - the requirement that a stage's own test suite passes before the next stage is built on top of it.

## Local development

Requires Python 3.10+.

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # fill in OPENAI_API_KEY
```

- LLM calls go through LangChain using OpenAI models; set `OPENAI_API_KEY` in `.env`.
- No external services required: SQLite and local filesystem storage both live under a local `data/` directory.
- No sample report is bundled in the repo (real corporate reports aren't ours to redistribute). Run `python scripts/make_sample_report.py` to generate a synthetic one, or upload any public sustainability report PDF via `POST /uploads`.
- Run the app: `uvicorn app.main:app --reload`.
- Run the test suite per stage: `pytest tests/stage_1`, `pytest tests/stage_2`, `pytest tests/stage_3`.
  Stage 1's tests run fully offline against a synthetic PDF fixture.
  Stage 2 and stage 3's tests call OpenAI directly and are skipped automatically unless `OPENAI_API_KEY` is set.

## Web UI

A minimal Next.js page in `web/` for manually exercising the pipeline: pick a PDF, upload it, watch the SSE stream update live, then browse the resulting reports, sections, and KPI values.

```
cd web
npm install
npm run dev
```

Then open `http://localhost:3000` with the FastAPI server (`uvicorn app.main:app --reload`) already running on `http://127.0.0.1:8000` - the two run as separate processes, connected over CORS.
The UI's SSE panel only shows stage start/complete events; the interesting detail (garbage-character checks, per-section word counts, each KPI candidate's accept/reject reason from the second-model validation call) prints to the `uvicorn` terminal, not the browser.

## Project conventions

- Each stage lives in its own module with its own fixtures and test suite; a stage isn't considered done until its tests pass.
- No distributed-systems or scaling work - single-process, single-node by design.
- This README should stay in sync with the pipeline as it's built; if the code and this document drift, fix the document.

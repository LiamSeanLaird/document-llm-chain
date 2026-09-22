"use client";

import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

type LogEntry = {
  event: string;
  data: Record<string, unknown>;
};

type Report = {
  id: string;
  url: string;
  xml: string;
};

type Section = {
  id: string;
  report_id: string;
  text: string;
  sort: number;
  topics: string[];
};

type KpiValueRow = {
  id: string;
  kpi_name: string;
  value: string;
  period: string;
  section_id: string;
  report_id: string;
};

type Tab = "kpi_values" | "sections" | "reports";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [tab, setTab] = useState<Tab>("kpi_values");
  const [reports, setReports] = useState<Report[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [kpiValues, setKpiValues] = useState<KpiValueRow[]>([]);

  async function refreshAll() {
    const [reportsRes, sectionsRes, valuesRes] = await Promise.all([
      fetch(`${API_BASE}/list_reports`),
      fetch(`${API_BASE}/list_sections`),
      fetch(`${API_BASE}/list_kpi_values`),
    ]);
    setReports(await reportsRes.json());
    setSections(await sectionsRes.json());
    setKpiValues(await valuesRes.json());
  }

  async function handleRun() {
    if (!file) return;

    setIsProcessing(true);
    setError(null);
    setLogs([]);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const uploadRes = await fetch(`${API_BASE}/uploads`, {
        method: "POST",
        body: formData,
      });
      if (!uploadRes.ok) throw new Error(`upload failed: ${uploadRes.status}`);
      const { reportUrl } = await uploadRes.json();

      const reportsRes = await fetch(`${API_BASE}/reports`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reportUrl }),
      });
      if (!reportsRes.ok || !reportsRes.body) {
        throw new Error(`processing failed: ${reportsRes.status}`);
      }

      await readSseStream(reportsRes.body, (entry) => {
        setLogs((prev) => [...prev, entry]);
      });

      await refreshAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsProcessing(false);
    }
  }

  return (
    <main>
      <h1>Document LLM Chain - test UI</h1>
      <p>Upload a sustainability report PDF and watch it move through the three-stage pipeline.</p>

      <div className="controls">
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <button onClick={handleRun} disabled={!file || isProcessing}>
          {isProcessing ? "Processing..." : "Upload & process"}
        </button>
        <button onClick={refreshAll} disabled={isProcessing}>
          Refresh tables
        </button>
      </div>

      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <h2>Progress</h2>
      <div className="log">
        {logs.length === 0
          ? "No events yet. Detailed step-by-step output (extraction stats, section word counts, KPI validation reasons) prints to the uvicorn server console, not here."
          : logs.map((entry, i) => (
              <div key={i}>
                [{entry.event}] {JSON.stringify(entry.data)}
              </div>
            ))}
      </div>

      <h2>Results</h2>
      <div className="tabs">
        <button data-active={tab === "kpi_values"} onClick={() => setTab("kpi_values")}>
          KPI values ({kpiValues.length})
        </button>
        <button data-active={tab === "sections"} onClick={() => setTab("sections")}>
          Sections ({sections.length})
        </button>
        <button data-active={tab === "reports"} onClick={() => setTab("reports")}>
          Reports ({reports.length})
        </button>
      </div>

      {tab === "kpi_values" && <KpiValuesTable rows={kpiValues} />}
      {tab === "sections" && <SectionsTable rows={sections} />}
      {tab === "reports" && <ReportsTable rows={reports} />}
    </main>
  );
}

function KpiValuesTable({ rows }: { rows: KpiValueRow[] }) {
  if (rows.length === 0) return <p>None yet.</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>KPI</th>
          <th>Value</th>
          <th>Period</th>
          <th>Section</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id}>
            <td>{row.kpi_name}</td>
            <td>{row.value}</td>
            <td>{row.period}</td>
            <td>{row.section_id.slice(0, 8)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function SectionsTable({ rows }: { rows: Section[] }) {
  if (rows.length === 0) return <p>None yet.</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Report</th>
          <th>Topics</th>
          <th>Text</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id}>
            <td>{row.sort}</td>
            <td>{row.report_id.slice(0, 8)}</td>
            <td>{row.topics.join(", ")}</td>
            <td>{row.text.length > 200 ? `${row.text.slice(0, 200)}...` : row.text}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ReportsTable({ rows }: { rows: Report[] }) {
  if (rows.length === 0) return <p>None yet.</p>;
  return (
    <>
      {rows.map((row) => (
        <details key={row.id} style={{ marginTop: 12 }}>
          <summary>
            {row.id.slice(0, 8)} - {row.url} ({row.xml.length} XML chars)
          </summary>
          <div className="xml-preview">{row.xml}</div>
        </details>
      ))}
    </>
  );
}

async function readSseStream(
  body: ReadableStream<Uint8Array>,
  onEvent: (entry: LogEntry) => void
) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary: number;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      onEvent(parseSseEvent(rawEvent));
    }
  }
}

function parseSseEvent(raw: string): LogEntry {
  let event = "message";
  let data = "{}";
  for (const line of raw.split("\n")) {
    if (line.startsWith("event: ")) event = line.slice("event: ".length);
    if (line.startsWith("data: ")) data = line.slice("data: ".length);
  }
  return { event, data: JSON.parse(data) };
}

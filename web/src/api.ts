// Typed client for the Jatayu FastAPI backend (same origin; works offline).
export type Span = [number, number];
export type FieldT<T> = { value: T | null; span: Span | null; confidence: number; source: string };
export type Flag = { code: string; field: string | null; severity: "high" | "medium" | "low"; message: string };
export type Medication = {
  kind: "medication"; id: string; drug: FieldT<string>; dose_value: FieldT<number>; dose_unit: FieldT<string>;
  route: FieldT<string>; time: FieldT<string>; flags: Flag[];
};
export type Procedure = {
  kind: "procedure"; id: string; procedure: FieldT<string>; time: FieldT<string>; detail: FieldT<string> | null; flags: Flag[];
};
export type Entry = Medication | Procedure;
export type Utterance = { id: string; transcript: string; capture_time: string; seq: number };
export type EntryState = { entry: Entry; status: "draft" | "edited" | "confirmed"; history: number[]; utterance_id: string };
export type Incident = { id: string; label: string | null; started_at: string };
export type IncidentState = Incident & { utterances: Utterance[]; entries: EntryState[] };
export type PipelineResult = {
  utterance: { id: string; raw_transcript: string; capture_time: string };
  entries: Entry[]; warnings: string[]; asr: { latency_s: number; device: string } | null;
};
export type Lexicon = {
  drugs: { name: string; aliases: string[]; routes: string[]; units: string[] }[];
  procedures: string[]; routes: string[]; units: string[];
};
export type AuditRow = { seq: number; ts: string; incident_id: string; event_type: string; entry_hash: string; prev_hash: string };
export type Verify = { ok: boolean; checked: number; first_bad_seq: number | null; reason: string | null };
export type Extractor = "hybrid" | "llm" | "rules";

export class ApiError extends Error {
  constructor(public status: number, public detail: unknown) {
    super(typeof detail === "string" ? detail : `HTTP ${status}`);
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, init);
  const body = r.headers.get("content-type")?.includes("json") ? await r.json() : await r.text();
  if (!r.ok) throw new ApiError(r.status, (body as { detail?: unknown })?.detail ?? body);
  return body as T;
}
const json = (method: string, body: unknown): RequestInit => ({
  method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
});

export const api = {
  health: () => call<{ ok: boolean; asr_device: string }>("/api/health"),
  lexicon: () => call<Lexicon>("/api/lexicon"),
  incidents: () => call<Incident[]>("/api/incidents"),
  createIncident: (label: string | null) => call<Incident>("/api/incidents", json("POST", { label })),
  incident: (id: string) => call<IncidentState>(`/api/incidents/${id}`),
  utterance: (incident: string, extractor: Extractor, input: { text?: string; audio?: Blob }) => {
    const f = new FormData();
    f.append("incident_id", incident);
    f.append("extractor", extractor);
    if (input.audio) f.append("audio", input.audio, "capture.webm");
    else f.append("text", input.text ?? "");
    return call<PipelineResult>("/api/utterances", { method: "POST", body: f });
  },
  edit: (incident: string, entry: Entry) =>
    call<{ seq: number; entry: Entry }>(`/api/incidents/${incident}/entries/${entry.id}/edit`, json("POST", { entry })),
  confirm: (incident: string, entry_ids: string[], acknowledged: string[], expected: Record<string, number>) =>
    call<{ seq: number }>(`/api/incidents/${incident}/confirm`, json("POST", { entry_ids, acknowledged, expected })),
  audit: () => call<AuditRow[]>("/api/audit"),
  verify: () => call<Verify>("/api/audit/verify"),
  readbackWav: (incident: string, entry: string) => `/api/incidents/${incident}/entries/${entry}/readback.wav`,
  readbackTxt: (incident: string, entry: string) =>
    fetch(`/api/incidents/${incident}/entries/${entry}/readback.txt`).then((r) => r.text()),
  pdf: (incident: string) => `/api/incidents/${incident}/note.pdf`,
  bundle: (incident: string) => `/api/incidents/${incident}/bundle`,
};

export const DISCLAIMER = "Decision-support demo, not a clinical device.";

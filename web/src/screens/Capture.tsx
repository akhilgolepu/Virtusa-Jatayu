import { useCallback, useEffect, useRef, useState } from "preact/hooks";
import { api, ApiError, type Entry, type Extractor, type Incident, type IncidentState, type Lexicon, type PipelineResult } from "../api";
import { EntryCard } from "../components/EntryCard";
import { Transcript } from "../components/Transcript";

const KEY = "jatayu-incident";
const fmt = (ms: number) => {
  const s = Math.floor(ms / 1000);
  return { main: `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`, tenths: `.${Math.floor((ms % 1000) / 100)}` };
};

function cells(e: Entry | undefined) {
  if (!e) return [["Drug", ""], ["Dose", ""], ["Route", ""], ["Time", ""]];
  const time = e.time.value ? new Date(e.time.value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "";
  if (e.kind === "procedure") return [["Procedure", e.procedure.value ?? ""], ["Detail", e.detail?.value ?? ""], ["", ""], ["Time", time]];
  const dose = e.dose_value.value === null ? "" : `${e.dose_value.value} ${e.dose_unit.value ?? "?"}`;
  return [["Drug", e.drug.value ?? ""], ["Dose", dose], ["Route", e.route.value ?? ""], ["Time", time]];
}

export function Capture() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [current, setCurrent] = useState<string>(() => { try { return localStorage.getItem(KEY) ?? ""; } catch { return ""; } });
  const [state, setState] = useState<IncidentState | null>(null);
  const [lexicon, setLexicon] = useState<Lexicon | null>(null);
  const [extractor, setExtractor] = useState<Extractor>("hybrid");
  const [label, setLabel] = useState("");
  const [text, setText] = useState("");
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState<PipelineResult | null>(null);
  const [error, setError] = useState("");
  const recorder = useRef<MediaRecorder | null>(null);
  const started = useRef(0);

  const refresh = useCallback(async (id = current) => {
    if (!id) { setState(null); return; }
    try { setState(await api.incident(id)); } catch { setState(null); setCurrent(""); }
  }, [current]);

  useEffect(() => { api.incidents().then(setIncidents).catch(() => {}); api.lexicon().then(setLexicon).catch(() => {}); }, []);
  useEffect(() => { try { localStorage.setItem(KEY, current); } catch { /* ignore */ } refresh(current); }, [current]);
  useEffect(() => {
    if (!recording) return;
    const t = setInterval(() => setElapsed(Date.now() - started.current), 100);
    return () => clearInterval(t);
  }, [recording]);

  async function newIncident() {
    const inc = await api.createIncident(label.trim() || null);
    setIncidents([inc, ...incidents]); setLabel(""); setCurrent(inc.id); setLast(null);
  }

  async function send(input: { text?: string; audio?: Blob }) {
    if (!current) { setError("Start or pick an incident first."); return; }
    setBusy(true); setError("");
    try {
      const r = await api.utterance(current, extractor, input);
      setLast(r); setText("");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? `${err.status}: ${err.message}` : "Could not reach the local server.");
    } finally { setBusy(false); }
  }

  const toggle = useCallback(async () => {
    if (recorder.current && recorder.current.state === "recording") { recorder.current.stop(); return; }
    if (!current || busy) { setError(current ? "" : "Start or pick an incident first."); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream); const chunks: Blob[] = [];
      rec.ondataavailable = (ev) => chunks.push(ev.data);
      rec.onstop = () => {
        stream.getTracks().forEach((t) => t.stop()); setRecording(false);
        send({ audio: new Blob(chunks, { type: rec.mimeType }) });
      };
      recorder.current = rec; started.current = Date.now(); setElapsed(0); setRecording(true); rec.start();
    } catch { setError("Microphone unavailable — use localhost or type instead."); }
  }, [current, busy, extractor]);

  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      const tag = (ev.target as HTMLElement).tagName;
      if (ev.code === "Space" && !["INPUT", "TEXTAREA", "SELECT", "BUTTON"].includes(tag) && !document.querySelector("dialog[open]")) {
        ev.preventDefault(); toggle();
      }
    };
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, [toggle]);

  const t = fmt(elapsed);
  const latest = last?.entries[last.entries.length - 1];
  const entries = state?.entries ?? [];

  return (
    <div class="workspace">
      <section class="stack" aria-label="Capture">
        <div class="card stack">
          <div class="row spread">
            <span class="label">Incident</span>
            {state && <a class="label" href={api.pdf(state.id)} target="_blank" rel="noopener">PDF note ↗</a>}
          </div>
          <select class="input" value={current} onChange={(ev) => setCurrent((ev.target as HTMLSelectElement).value)} aria-label="Current incident">
            <option value="">— choose an incident —</option>
            {incidents.map((i) => (
              <option key={i.id} value={i.id}>{i.label || "Unlabelled"} · {new Date(i.started_at).toLocaleString([], { dateStyle: "short", timeStyle: "short" })}</option>
            ))}
          </select>
          <form class="row" onSubmit={(ev) => { ev.preventDefault(); newIncident(); }}>
            <input class="input" style={{ flex: 1 }} placeholder="New incident label (optional)" value={label}
                   onInput={(ev) => setLabel((ev.target as HTMLInputElement).value)} aria-label="New incident label" />
            <button class="btn" type="submit">New incident</button>
          </form>
        </div>

        <div class="card recorder">
          <div class="row spread">
            <span class="label">{recording ? <><span class="live-dot" /> recording</> : busy ? "processing…" : "ready"}</span>
            <div class="seg" role="group" aria-label="Extractor">
              {(["hybrid", "llm", "rules"] as Extractor[]).map((x) => (
                <button key={x} aria-pressed={extractor === x} onClick={() => setExtractor(x)}>{x}</button>
              ))}
            </div>
          </div>
          <div class="timer" data-live={recording} aria-live="off">{t.main}<span class="tenths">{t.tenths}</span></div>
          <div class="row">
            <button class="btn btn-record" aria-pressed={recording} onClick={toggle} disabled={busy && !recording}>
              {recording ? "■ Stop" : "● Record"} <kbd>Space</kbd>
            </button>
          </div>
          <form class="row" onSubmit={(ev) => { ev.preventDefault(); if (text.trim()) send({ text }); }}>
            <input class="input" style={{ flex: 1 }} placeholder="Or type: gave 4 mg ondansetron IV two mins ago" value={text}
                   onInput={(ev) => setText((ev.target as HTMLInputElement).value)} aria-label="Type an utterance" />
            <button class="btn btn-primary" type="submit" disabled={busy || !text.trim()} data-state={busy ? "loading" : undefined}>Send</button>
          </form>
          {error && <p role="alert" class="banner" data-tone="bad">{error}</p>}
          {last?.warnings.map((w) => <p key={w} class="label">{w}</p>)}
        </div>

        <div class="cells" aria-label="Latest entry">
          {cells(latest).map(([k, v], i) => (
            <div class="cell" key={i}><div class="label">{k || " "}</div><div class={`value${v ? "" : " empty"}`}>{v || "—"}</div></div>
          ))}
        </div>

        {last && (
          <div class="card stack">
            <span class="label">Last transcript{last.asr ? ` · ASR ${last.asr.latency_s.toFixed(2)} s on ${last.asr.device}` : ""}</span>
            <Transcript text={last.utterance.raw_transcript} entries={last.entries} />
          </div>
        )}
      </section>

      <section class="stack" aria-label="Review">
        <div class="row spread">
          <h2>{state?.label || (state ? "Incident" : "Review")}</h2>
          {state && <span class="label">{entries.length} entr{entries.length === 1 ? "y" : "ies"} · {state.utterances.length} utterance{state.utterances.length === 1 ? "" : "s"}</span>}
        </div>
        {!state && <p class="muted">Start a new incident, then speak or type what was given. Each entry appears here for review.</p>}
        {state && !entries.length && <p class="muted">Nothing recorded yet. Press Space and say, for example, “gave 0.3 milligrams of adrenaline IM”.</p>}
        {[...entries].reverse().map((s) => (
          <EntryCard key={s.entry.id + s.history.length} incident={state!.id} state={s} n={entries.indexOf(s) + 1} lexicon={lexicon} onChange={() => refresh()} />
        ))}
      </section>
    </div>
  );
}

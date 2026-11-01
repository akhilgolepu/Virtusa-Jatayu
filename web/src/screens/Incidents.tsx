import { useEffect, useState } from "preact/hooks";
import { api, type Incident, type IncidentState } from "../api";
import { Flags } from "../components/Flags";
import { link } from "../router";

const when = (iso: string) => new Date(iso).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
const hhmm = (iso: string | null) => (iso ? new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—");

function Timeline({ id }: { id: string }) {
  const [s, setS] = useState<IncidentState | null>(null);
  useEffect(() => { api.incident(id).then(setS).catch(() => setS(null)); }, [id]);
  if (!s) return <p class="muted">Loading…</p>;
  const items = [...s.entries].sort((a, b) => (a.entry.time.value ?? "").localeCompare(b.entry.time.value ?? ""));
  return (
    <div class="stack">
      <a class="label" {...link("/incidents")}>← all incidents</a>
      <h1>{s.label || "Unlabelled incident"}</h1>
      <div class="row">
        <span class="muted">Started {when(s.started_at)}</span>
        <a class="btn" href={api.pdf(id)} target="_blank" rel="noopener">PDF note</a>
        <a class="btn" href={api.bundle(id)} target="_blank" rel="noopener">FHIR-lite JSON</a>
      </div>
      <div class="scroll-x">
        <table class="ledger">
          <thead><tr><th>Time</th><th>Entry</th><th>Status</th><th>Checks</th></tr></thead>
          <tbody>
            {items.map(({ entry: e, status }) => (
              <tr key={e.id}>
                <td class="mono">{hhmm(e.time.value)}</td>
                <td>{e.kind === "medication"
                  ? `${e.drug.value} ${e.dose_value.value ?? "?"} ${e.dose_unit.value ?? ""} ${e.route.value ?? ""}`
                  : `${e.procedure.value}${e.detail?.value ? ` (${e.detail.value})` : ""}`}</td>
                <td><span class="status" data-status={status}>{status}</span></td>
                <td style={{ minWidth: "16rem" }}><Flags flags={e.flags} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3>Utterances</h3>
      {s.utterances.map((u) => (
        <p key={u.id}><span class="mono label">{hhmm(u.capture_time)} · seq {u.seq}</span><br />{u.transcript || <em>(no speech)</em>}</p>
      ))}
    </div>
  );
}

export function Incidents({ id }: { id?: string }) {
  const [list, setList] = useState<Incident[] | null>(null);
  useEffect(() => { if (!id) api.incidents().then(setList).catch(() => setList([])); }, [id]);
  if (id) return <Timeline id={id} />;
  return (
    <div class="stack">
      <h1>Incidents</h1>
      {list === null && <p class="muted">Loading…</p>}
      {list?.length === 0 && <p class="muted">No incidents yet. Start one on the Capture screen.</p>}
      <div>{list?.map((i) => (
        <a key={i.id} class="list-link" {...link(`/incidents/${i.id}`)}>
          <strong>{i.label || "Unlabelled incident"}</strong>
          <span class="label">{when(i.started_at)} · {i.id.slice(0, 8)}</span>
        </a>
      ))}</div>
    </div>
  );
}

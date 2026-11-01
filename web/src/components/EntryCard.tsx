import { useRef, useState } from "preact/hooks";
import { api, ApiError, type Entry, type EntryState, type Lexicon } from "../api";
import { Flags } from "./Flags";

const fmtTime = (iso: string | null) =>
  iso ? new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—";

function Field({ label, value, user }: { label: string; value: string; user?: boolean }) {
  return (
    <div>
      <div class="label">{label}</div>
      <div class={`v${user ? " user" : ""}`} title={user ? "edited by you" : undefined}>{value}</div>
    </div>
  );
}

export function EntryCard({ incident, state, n, lexicon, onChange }: {
  incident: string; state: EntryState; n: number; lexicon: Lexicon | null; onChange: () => void;
}) {
  const e = state.entry;
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Entry>(e);
  const [busy, setBusy] = useState<"" | "save" | "confirm" | "play">("");
  const [error, setError] = useState("");
  const [ack, setAck] = useState<string[]>([]);
  const dialog = useRef<HTMLDialogElement>(null);
  const audio = useRef<HTMLAudioElement>(null);
  const high = e.flags.filter((f) => f.severity === "high");
  const confirmed = state.status === "confirmed";

  const title = e.kind === "medication" ? e.drug.value ?? "Unknown drug" : e.procedure.value ?? "Procedure";
  const drugInfo = e.kind === "medication" ? lexicon?.drugs.find((d) => d.name === e.drug.value) : undefined;

  async function save() {
    setBusy("save"); setError("");
    try { await api.edit(incident, draft); setEditing(false); onChange(); }
    catch (err) { setError(err instanceof ApiError ? String(err.message) : "Could not save the edit."); }
    finally { setBusy(""); }
  }

  async function confirm(acknowledged: string[]) {
    setBusy("confirm"); setError("");
    try { await api.confirm(incident, [e.id], acknowledged); dialog.current?.close(); onChange(); }
    catch (err) { setError(err instanceof ApiError && err.status === 409 ? "Acknowledge every check first." : "Could not confirm."); }
    finally { setBusy(""); }
  }

  function startConfirm() {
    if (high.length) { setAck([]); dialog.current?.showModal(); } else confirm([]);
  }

  function play() {
    if (!audio.current) return;
    setBusy("play");
    audio.current.src = api.readbackWav(incident, e.id) + `?v=${state.history.length}`;
    audio.current.play().catch(() => setError("Could not play the read-back.")).finally(() => setBusy(""));
  }

  return (
    <article class="card entry" aria-label={`Entry ${n}: ${title}`}>
      <div class="entry-head">
        <span class="entry-num">{String(n).padStart(2, "0")}</span>
        <h3>{title}</h3>
        <span class="status" data-status={state.status}>{state.status}</span>
      </div>

      {e.kind === "medication" && !editing && (
        <div class="fields">
          <Field label="Dose" value={e.dose_value.value === null ? "not stated" : `${e.dose_value.value}`} user={e.dose_value.source === "user"} />
          <Field label="Unit" value={e.dose_unit.value ?? "not stated"} user={e.dose_unit.source === "user"} />
          <Field label="Route" value={e.route.value ?? "not stated"} user={e.route.source === "user"} />
          <Field label="Time" value={fmtTime(e.time.value)} user={e.time.source === "user"} />
        </div>
      )}
      {e.kind === "procedure" && (
        <div class="fields">
          <Field label="Detail" value={e.detail?.value ?? "—"} />
          <Field label="Time" value={fmtTime(e.time.value)} />
        </div>
      )}

      {editing && draft.kind === "medication" && (
        <form class="fields" onSubmit={(ev) => { ev.preventDefault(); save(); }}>
          <label><span class="label">Dose</span>
            <input class="input mono" inputMode="decimal" value={draft.dose_value.value ?? ""}
                   onInput={(ev) => { const v = (ev.target as HTMLInputElement).value; setDraft({ ...draft, dose_value: { ...draft.dose_value, value: v === "" ? null : Number(v) } }); }} /></label>
          <label><span class="label">Unit</span>
            <select class="input" value={draft.dose_unit.value ?? ""}
                    onChange={(ev) => setDraft({ ...draft, dose_unit: { ...draft.dose_unit, value: (ev.target as HTMLSelectElement).value || null } })}>
              <option value="">not stated</option>
              {(drugInfo?.units ?? lexicon?.units ?? []).map((u) => <option key={u} value={u}>{u}</option>)}
            </select></label>
          <label><span class="label">Route</span>
            <select class="input" value={draft.route.value ?? ""}
                    onChange={(ev) => setDraft({ ...draft, route: { ...draft.route, value: (ev.target as HTMLSelectElement).value || null } })}>
              <option value="">not stated</option>
              {(drugInfo?.routes ?? lexicon?.routes ?? []).map((r) => <option key={r} value={r}>{r}</option>)}
            </select></label>
          <div class="row" style={{ alignSelf: "end" }}>
            <button class="btn btn-primary" type="submit" data-state={busy === "save" ? "loading" : undefined} disabled={busy !== ""}>Save edit</button>
            <button class="btn btn-ghost" type="button" onClick={() => { setDraft(e); setEditing(false); }}>Cancel</button>
          </div>
        </form>
      )}

      <Flags flags={e.flags} />
      {error && <p role="alert" class="banner" data-tone="bad">{error}</p>}

      <div class="row">
        <button class="btn" onClick={play} data-state={busy === "play" ? "loading" : undefined} disabled={busy !== ""}>▶ Read back</button>
        {e.kind === "medication" && !confirmed && !editing && (
          <button class="btn" onClick={() => { setDraft(e); setEditing(true); }}>Edit</button>
        )}
        {!confirmed && (
          <button class="btn btn-primary" onClick={startConfirm} data-state={busy === "confirm" ? "loading" : undefined} disabled={busy !== "" || editing}>
            Confirm
          </button>
        )}
        <span class="label">history: {state.history.length} row{state.history.length === 1 ? "" : "s"}</span>
      </div>
      <audio ref={audio} preload="none" />

      <dialog ref={dialog} aria-labelledby={`ack-${e.id}`}>
        <div class="stack">
          <h3 id={`ack-${e.id}`}>Check before confirming</h3>
          <p class="muted">This entry has {high.length} high-severity check{high.length === 1 ? "" : "s"}. Confirm only if each one is understood.</p>
          {high.map((f) => (
            <label class="check" key={f.code}>
              <input type="checkbox" checked={ack.includes(f.code)}
                     onChange={(ev) => setAck((ev.target as HTMLInputElement).checked ? [...ack, f.code] : ack.filter((c) => c !== f.code))} />
              <span><code>{f.code.replaceAll("_", " ")}</code> — {f.message}</span>
            </label>
          ))}
          <div class="row">
            <button class="btn btn-primary" disabled={ack.length < high.length || busy !== ""} onClick={() => confirm(ack)}>Confirm with checks</button>
            <button class="btn btn-ghost" onClick={() => dialog.current?.close()}>Back</button>
          </div>
        </div>
      </dialog>
    </article>
  );
}

import { useRef, useState } from "preact/hooks";
import { api, ApiError, type Entry, type EntryState, type Lexicon } from "../api";
import { Flags } from "./Flags";

// Units in full next to the code (round 10): "mg · milligrams".
const UNIT_WORDS: Record<string, string> = {
  mg: "milligrams", mcg: "micrograms", g: "grams", ml: "millilitres", "L/min": "litres per minute", units: "units",
  puffs: "puffs", drops: "drops", mmol: "millimoles", mEq: "milliequivalents",
};

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
  const [busy, setBusy] = useState<"" | "save" | "confirm" | "play" | "reject">("");
  const [error, setError] = useState("");
  const [ack, setAck] = useState<string[]>([]);
  const dialog = useRef<HTMLDialogElement>(null);
  const audio = useRef<HTMLAudioElement>(null);
  const high = e.flags.filter((f) => f.severity === "high");
  // One tick per distinct check: two flags can share a code (e.g. llm_unsupported on two fields).
  const highCodes = [...new Set(high.map((f) => f.code))];
  const confirmed = state.status === "confirmed";
  const rejected = state.status === "rejected";
  const settled = confirmed || rejected;

  const title = e.kind === "medication" ? e.drug.value ?? "Unknown drug" : e.procedure.value ?? "Procedure";
  const drugInfo = e.kind === "medication" ? lexicon?.drugs.find((d) => d.name === e.drug.value) : undefined;
  // Round 9: the word as heard is never hidden. It shows next to the recorded drug whenever the two differ; a drug
  // matched only by sound (sound_alike_drug) also gets a "did you mean ...?" box and must be ticked to confirm.
  const letters = (s: string | null | undefined) => (s ?? "").toLowerCase().replace(/[^a-z]/g, "");
  const heard = e.kind === "medication" && e.drug.raw && letters(e.drug.raw) !== letters(e.drug.value) ? e.drug.raw : null;
  const soundAlike = e.flags.find((f) => f.code === "sound_alike_drug");

  async function save() {
    setBusy("save"); setError("");
    try { await api.edit(incident, draft); setEditing(false); onChange(); }
    catch (err) { setError(err instanceof ApiError ? String(err.message) : "Could not save the edit."); }
    finally { setBusy(""); }
  }

  async function confirm(acknowledged: string[]) {
    setBusy("confirm"); setError("");
    try { await api.confirm(incident, [e.id], acknowledged, { [e.id]: state.history[state.history.length - 1] }); dialog.current?.close(); onChange(); }
    catch (err) {
      const stale = err instanceof ApiError && JSON.stringify(err.detail).includes("stale");
      setError(stale ? "This entry changed since you opened it — reloading." : err instanceof ApiError && err.status === 409 ? "Acknowledge every check first." : "Could not confirm.");
      if (stale) onChange();
    }
    finally { setBusy(""); }
  }

  async function reject() {
    setBusy("reject"); setError("");
    try { await api.reject(incident, e.id, null); onChange(); }
    catch { setError("Could not reject."); }
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
    <article class="card entry" data-status={state.status} aria-label={`Entry ${n}: ${title}`}>
      <div class="entry-head">
        <span class="entry-num">{String(n).padStart(2, "0")}</span>
        {/* Round 10: drug identity is the most prominent element of the card (presentation only; not claimed to catch
            a wrong drug). */}
        <div class="identity">
          {e.kind === "medication" && <span class="label">Drug</span>}
          <h3 class={e.kind === "medication" ? "drug-name" : undefined}>{title}</h3>
          {heard && <span class="heard" title="the word as the recogniser heard it">heard “{heard}”</span>}
        </div>
        <span class="status" data-status={state.status}>{state.status}</span>
      </div>
      {soundAlike && e.kind === "medication" && !settled && (
        <p class="banner did-you-mean" data-tone="bad" role="note">
          ▲ Heard <b>“{e.drug.raw}”</b> — did you mean <b>{e.drug.value}</b>? Matched by sound only. Confirm only if it is
          this drug; otherwise reject and re-dictate.
        </p>
      )}

      {e.kind === "medication" && !editing && (
        <div class="fields">
          <Field label="Dose" value={e.dose_value.value === null ? "not stated" : `${e.dose_value.value}`} user={e.dose_value.source === "user"} />
          <Field label="Unit" value={e.dose_unit.value ? `${e.dose_unit.value} · ${UNIT_WORDS[e.dose_unit.value] ?? e.dose_unit.value}` : "not stated"} user={e.dose_unit.source === "user"} />
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
        {e.kind === "medication" && !settled && !editing && (
          <button class="btn" onClick={() => { setDraft(e); setEditing(true); }}>Edit</button>
        )}
        {!settled && !editing && (
          <button class="btn btn-ghost" onClick={reject} data-state={busy === "reject" ? "loading" : undefined} disabled={busy !== ""}>Reject</button>
        )}
        {!settled && (
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
          <p class="muted">This entry has {highCodes.length} high-severity check{highCodes.length === 1 ? "" : "s"}. Confirm only if each one is understood.</p>
          {e.kind === "medication" && (
            <div class="identity-check">
              <div><span class="label">Drug</span> <span class="drug-name">{e.drug.value ?? "—"}</span></div>
              <div><span class="label">Heard</span> “{e.drug.raw ?? "—"}”</div>
            </div>
          )}
          {highCodes.map((code) => (
            <label class="check" key={code}>
              <input type="checkbox" checked={ack.includes(code)}
                     onChange={(ev) => setAck((ev.target as HTMLInputElement).checked ? [...ack, code] : ack.filter((c) => c !== code))} />
              <span><code>{code.replaceAll("_", " ")}</code> — {high.filter((f) => f.code === code).map((f) => f.message).join(" ")}</span>
            </label>
          ))}
          <div class="row">
            <button class="btn btn-primary" disabled={highCodes.some((c) => !ack.includes(c)) || busy !== ""} onClick={() => confirm(ack)}>{e.kind === "medication" && e.drug.value ? `Confirm ${e.drug.value}` : "Confirm with checks"}</button>
            <button class="btn btn-ghost" onClick={() => dialog.current?.close()}>Back</button>
          </div>
        </div>
      </dialog>
    </article>
  );
}

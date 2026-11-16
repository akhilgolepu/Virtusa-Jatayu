import { useCallback, useEffect, useRef, useState } from "preact/hooks";

type Prompt = { prompt_id: string; text: string; condition_hint: string; status: string; lang?: string };
type Take = { take_id?: string; status?: string; wer?: number | null; asr_text?: string | null; gold_field_mismatch?: string[]; detail?: string };

// Record-corpus page (speakers read the prompts aloud; ?part=N&parts=3 = one speaker's share, docs/recording_guide.md). Keys: Space record/stop · Enter next · R re-record · E edit.
export function Record() {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [idx, setIdx] = useState(0);
  const [recording, setRecording] = useState(false);
  const [take, setTake] = useState<Take | null>(null);
  const [editing, setEditing] = useState(false);
  const [gold, setGold] = useState("");
  const rec = useRef<MediaRecorder | null>(null);

  // ?part=N&parts=3: one speaker's share of the prompts (docs/recording_guide.md); without it, every prompt.
  const query = new URLSearchParams(location.search);
  const part = query.get("part");
  const parts = query.get("parts") ?? "3";
  useEffect(() => {
    fetch(`/api/corpus/prompts?status=all${part ? `&part=${encodeURIComponent(part)}&parts=${encodeURIComponent(parts)}` : ""}`)
      .then((r) => r.json()).then((all: Prompt[]) => {
      setPrompts(all);
      setIdx(Math.max(0, all.findIndex((p) => p.status === "todo" || p.status === "rerecord")));
    });
  }, []);

  const p = prompts[idx];
  const done = prompts.filter((x) => x.status !== "todo" && x.status !== "rerecord").length;

  function apply(row: Take) {
    setTake(row);
    if (row.status) setPrompts((ps) => ps.map((x, i) => (i === idx ? { ...x, status: row.status! } : x)));
  }

  const toggle = useCallback(async () => {
    if (rec.current && rec.current.state === "recording") { rec.current.stop(); return; }
    if (!p) return;
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const r = new MediaRecorder(stream); const chunks: Blob[] = [];
    r.ondataavailable = (e) => chunks.push(e.data);
    r.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop()); setRecording(false);
      const f = new FormData();
      f.append("prompt_id", p.prompt_id); f.append("condition", p.condition_hint);
      f.append("audio", new Blob(chunks, { type: r.mimeType }), "take.webm");
      setTake({ detail: "checking…" });
      apply(await (await fetch("/api/corpus/recordings", { method: "POST", body: f })).json());
    };
    rec.current = r; setRecording(true); r.start();
  }, [p, idx]);

  async function resolve(action: "rerecord" | "keep_edited", gold_text?: string) {
    if (!take?.take_id) return;
    const r = await fetch(`/api/corpus/recordings/${take.take_id}/resolve`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action, gold_text }),
    });
    apply(await r.json()); setEditing(false);
  }

  const next = () => { setIdx((i) => Math.min(prompts.length - 1, i + 1)); setTake(null); setEditing(false); };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).tagName === "TEXTAREA") return;
      if (e.code === "Space") { e.preventDefault(); toggle(); }
      else if (e.key === "Enter") next();
      else if (e.key.toLowerCase() === "r") resolve("rerecord");
      else if (e.key.toLowerCase() === "e") { e.preventDefault(); setGold(p?.text ?? ""); setEditing(true); }
    };
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, [toggle, p, take]);

  if (!prompts.length) return <p class="muted">No prompts. Run <code>python -m datagen.prompts</code> and reload.</p>;
  return (
    <div class="stack" style={{ maxWidth: "52rem" }}>
      <div class="row spread"><span class="label">{part ? `Part ${part} of ${parts} · ` : ""}{done} / {prompts.length} recorded · {p?.prompt_id}</span><span class="label">condition: {p?.condition_hint}</span></div>
      <div class="progress"><div style={{ width: `${(100 * done) / prompts.length}%` }} /></div>
      <p class="prompt">{p?.text}</p>
      <div class="row">
        <button class="btn btn-record" aria-pressed={recording} onClick={toggle}>{recording ? "■ Stop" : "● Record"} <kbd>Space</kbd></button>
        <button class="btn" onClick={next}>Next <kbd>Enter</kbd></button>
        <button class="btn" onClick={() => resolve("rerecord")} disabled={!take?.take_id}>Re-record <kbd>R</kbd></button>
        <button class="btn" onClick={() => { setGold(p.text); setEditing(true); }} disabled={!take?.take_id}>Said it differently <kbd>E</kbd></button>
      </div>
      {take && (
        <div class="card stack">
          <div class="row"><span class="status" data-status={take.status === "ok" || take.status === "keep_edited" || take.status === "sealed" ? "confirmed" : "edited"}>{take.status ?? "…"}</span>
            {take.wer != null && <span class="label">WER {take.wer.toFixed(2)}</span>}
            {take.gold_field_mismatch?.length ? <span class="label">▲ not heard: {take.gold_field_mismatch.join(", ")}</span> : null}</div>
          <p class="muted">{take.status === "sealed"
            ? "Test take saved, sealed: not transcribed. Listen back if unsure; R to re-record."
            : take.asr_text ?? take.detail}</p>
        </div>
      )}
      {editing && (
        <form class="stack" onSubmit={(e) => { e.preventDefault(); resolve("keep_edited", gold); }}>
          <span class="label">Type exactly what you said — labels are realigned to it, or the take is marked for annotation.</span>
          <textarea class="input" rows={3} value={gold} onInput={(e) => setGold((e.target as HTMLTextAreaElement).value)} />
          <div class="row"><button class="btn btn-primary" type="submit">Save edited text</button>
            <button class="btn btn-ghost" type="button" onClick={() => setEditing(false)}>Cancel</button></div>
        </form>
      )}
    </div>
  );
}

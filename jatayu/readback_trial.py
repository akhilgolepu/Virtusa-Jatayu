"""Read-back test harness (evaluator round 12, item 3). SEPARATE from the pipeline: its own small app and its own
store; it only reuses the read-back voice (jatayu.readback) and the lexicon. Nothing here changes how dictation is
extracted, validated, confirmed or stored.

A tester with an anonymous ID (letters + digits, e.g. "T01"; never a name) gets 24 synthetic records in a seeded random
order: 10 correct, 6 with a wrong but valid drug, 4 with an in-range wrong dose, 4 with a wrong route. Each trial first
shows the order to say aloud ("Gave 4 milligrams ondansetron intravenous"), then hides it and shows the RECORD on a
confirm-style card while the read-back speaks it. The tester presses "Confirm" or "Needs correction". The page is shown
nothing about errors, flags, the mix or counts; the answer key (which trials are wrong, and how) stays in the server's
store and is never sent. Every wrong record is still VALID (the validator raises no flag on it), so only the tester's
own check can catch it. Stored per answer: tester ID, trial token, answer, response time. No names, audio or
transcripts are stored."""
from __future__ import annotations

import json
import random
import re
import secrets
import threading
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from jatayu.lexicon import Lexicon

STUDY_SEED = "scribe108-readback-v1"
MIX = {"correct": 10, "wrong_drug": 6, "wrong_dose": 4, "wrong_route": 4}
TYPES = tuple(MIX)
ID_PATTERN = re.compile(r"^[A-Z]{1,3}[0-9]{2,3}$")  # "T01", "RB012": anonymous codes only, never a name
ANSWERS = ("confirm", "needs_correction")


# ---- synthetic records -------------------------------------------------------------------------------------------
def _clean(lex: Lexicon, drug: str, dose: float, unit: str, route: str) -> bool:
    """A record the validator raises NO flag on (in a cited range, allowed unit and route)."""
    from jatayu.models import Field, MedicationEntry
    from jatayu.validate import validate

    f = lambda v: Field(value=v, span=None, confidence=1.0, source="user")  # noqa: E731
    e = MedicationEntry(drug=f(drug), dose_value=f(dose), dose_unit=f(unit), route=f(route),
                        time=f(datetime(2026, 1, 1).astimezone()), flags=[])
    return not validate(e, lex)


def _doses(lo: float, hi: float) -> list[float]:
    mid = (lo + hi) / 2
    nice = round(mid, 1) if mid < 10 else round(mid)
    return sorted({lo, hi, nice})


@lru_cache(maxsize=1)
def pool() -> tuple[dict, ...]:
    """Every (drug, dose, unit, route) the lexicon's cited dose bands allow with no flag, with its valid variants."""
    lex = Lexicon.load()
    base = []
    for drug in lex.drug_names():
        info = lex.drug(drug)
        for r in info.dose_ranges:
            if r.min is None or r.max is None or r.per_kg is not None or r.route not in info.routes:
                continue
            for dose in _doses(r.min, r.max):
                if _clean(lex, drug, dose, r.unit, r.route):
                    base.append({"drug": drug, "dose": dose, "unit": r.unit, "route": r.route})
    uniq = {(b["drug"], b["dose"], b["unit"], b["route"]): b for b in base}
    out = []
    for b in uniq.values():
        d, v, u, ro = b["drug"], b["dose"], b["unit"], b["route"]
        drugs = sorted(x for x in lex.drug_names() if x != d and _clean(lex, x, v, u, ro))
        doses = sorted({k[1] for k in uniq if k[0] == d and k[2] == u and k[3] == ro and k[1] != v})
        routes = sorted(x for x in lex.drug(d).routes if x != ro and _clean(lex, d, v, u, x))
        out.append({**b, "alt": {"wrong_drug": drugs, "wrong_dose": doses, "wrong_route": routes}})
    return tuple(sorted(out, key=lambda b: (b["drug"], b["route"], b["unit"], b["dose"])))


def trials_for(tester_id: str) -> list[dict]:
    """The tester's 24 trials (with the key), deterministic per ID: the same ID always gets the same set and order."""
    rng = random.Random(f"{STUDY_SEED}:{tester_id}")
    candidates = list(pool())
    rng.shuffle(candidates)
    used, trials = set(), []
    for kind, n in sorted(MIX.items(), key=lambda kv: kv[0] == "correct"):  # wrong kinds first: they need variants
        for b in candidates:
            if sum(t["type"] == kind for t in trials) == n:
                break
            if b["drug"] in used or (kind != "correct" and not b["alt"][kind]):
                continue  # one trial per drug: a tester must not judge one record by remembering another
            said = {k: b[k] for k in ("drug", "dose", "unit", "route")}
            record = dict(said)
            if kind != "correct":
                record[{"wrong_drug": "drug", "wrong_dose": "dose", "wrong_route": "route"}[kind]] = rng.choice(b["alt"][kind])
            used.add(b["drug"])
            trials.append({"type": kind, "said": said, "record": record})
    if [sum(t["type"] == k for t in trials) for k in TYPES] != list(MIX.values()):
        raise RuntimeError("the lexicon cannot supply the trial mix")
    rng.shuffle(trials)
    return trials


def _words(record: dict) -> dict:
    from jatayu.readback import ROUTE_WORDS, _unit

    return {"unit_words": _unit(record["unit"], record["dose"]), "route_words": ROUTE_WORDS.get(record["route"], record["route"])}


def say_text(said: dict) -> str:
    w = _words(said)
    return f"Gave {said['dose']:g} {w['unit_words']} {said['drug']} {w['route_words']}."


def public(trial: dict) -> dict:
    """What the page may see: the order to say and the record. Never the type, never the key."""
    r = trial["record"]
    return {"token": trial["token"], "say": say_text(trial["said"]),
            "record": {"drug": r["drug"], "dose": f"{r['dose']:g}", "unit": r["unit"], "route": r["route"], **_words(r)}}


# ---- store -------------------------------------------------------------------------------------------------------
class TrialStore:
    """sessions/<tester>.json holds the key (server side only); responses.jsonl holds the answers."""

    def __init__(self, root: Path):
        self.root = Path(root)
        (self.root / "sessions").mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, tester: str) -> Path:
        return self.root / "sessions" / f"{tester}.json"

    def session(self, tester: str) -> dict:
        with self._lock:
            p = self._path(tester)
            if p.exists():
                return json.loads(p.read_text())
            trials = trials_for(tester)
            for t in trials:
                t["token"] = secrets.token_hex(12)
            s = {"tester": tester, "created": datetime.now().astimezone().isoformat(), "trials": trials, "answers": {}}
            p.write_text(json.dumps(s, indent=1))
            return s

    def next_trial(self, s: dict) -> dict | None:
        return next((t for t in s["trials"] if t["token"] not in s["answers"]), None)

    def answer(self, tester: str, token: str, answer: str, ms: int | None) -> dict:
        with self._lock:
            p = self._path(tester)
            s = json.loads(p.read_text())
            current = next((t for t in s["trials"] if t["token"] not in s["answers"]), None)
            if current is None or current["token"] != token:
                raise LookupError("not the current trial")
            row = {"tester": tester, "token": token, "answer": answer, "ms": ms,
                   "at": datetime.now().astimezone().isoformat()}
            s["answers"][token] = row
            p.write_text(json.dumps(s, indent=1))
            with open(self.root / "responses.jsonl", "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row) + "\n")
            return s

    def trial(self, tester: str, token: str) -> dict | None:
        p = self._path(tester)
        if not p.exists():
            return None
        return next((t for t in json.loads(p.read_text())["trials"] if t["token"] == token), None)

    def sessions(self) -> list[dict]:
        return [json.loads(p.read_text()) for p in sorted((self.root / "sessions").glob("*.json"))]


# ---- aggregate ---------------------------------------------------------------------------------------------------
def aggregate(store: TrialStore) -> dict:
    """Catch rate per error type and false-alarm rate on correct records, with Wilson 95% CIs. Aggregate only."""
    from eval.stats import wilson

    n = {k: 0 for k in TYPES}
    flagged = {k: 0 for k in TYPES}
    sessions = store.sessions()
    for s in sessions:
        for t in s["trials"]:
            a = s["answers"].get(t["token"])
            if a is not None:
                n[t["type"]] += 1
                flagged[t["type"]] += a["answer"] == "needs_correction"

    def rate(k: int, m: int) -> dict:
        lo, hi = wilson(k, m) if m else (0.0, 0.0)
        return {"count": k, "denominator": m, "rate": round(k / m, 4) if m else None,
                "wilson95": [round(lo, 4), round(hi, 4)] if m else None}

    return {"testers": len(sessions),
            "testers_complete": sum(len(s["answers"]) == len(s["trials"]) for s in sessions),
            "catch_rate": {k: rate(flagged[k], n[k]) for k in TYPES if k != "correct"},
            "catch_rate_all_errors": rate(sum(flagged[k] for k in TYPES if k != "correct"),
                                          sum(n[k] for k in TYPES if k != "correct")),
            "false_alarm_rate": rate(flagged["correct"], n["correct"])}


# ---- app ---------------------------------------------------------------------------------------------------------
from pydantic import BaseModel  # noqa: E402  (module level: FastAPI must resolve these annotations)


class SessionIn(BaseModel):
    tester_id: str


class AnswerIn(BaseModel):
    tester_id: str
    token: str
    answer: str
    ms: int | None = None


def create_readback_app(store_dir: Path, synth=None):
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse, Response

    from jatayu.config import DISCLAIMER

    store = TrialStore(store_dir)
    app = FastAPI(title="Scribe108 read-back test", description=DISCLAIMER)

    def _id(tester: str) -> str:
        if not ID_PATTERN.match(tester or ""):
            raise HTTPException(422, "use the anonymous tester code you were given (capital letters then digits, e.g. T01)")
        return tester

    def _state(s: dict) -> dict:
        t = store.next_trial(s)
        return {"done": t is None, "trial": public(t) if t else None}

    @app.get("/readback-test", response_class=HTMLResponse)
    def page():
        return PAGE.replace("{{DISCLAIMER}}", DISCLAIMER)

    @app.post("/api/readback-test/session")
    def session(body: SessionIn):
        return _state(store.session(_id(body.tester_id)))

    @app.post("/api/readback-test/answer")
    def answer(body: AnswerIn):
        if body.answer not in ANSWERS:
            raise HTTPException(422, f"answer must be one of {ANSWERS}")
        try:
            s = store.answer(_id(body.tester_id), body.token, body.answer, body.ms)
        except (LookupError, FileNotFoundError) as exc:
            raise HTTPException(409, "not the current trial") from exc
        return _state(s)

    @app.get("/api/readback-test/audio/{tester_id}/{token}")
    def audio(tester_id: str, token: str):
        t = store.trial(_id(tester_id), token)
        if t is None:
            raise HTTPException(404, "unknown trial")
        return Response((synth or _speak)(t["record"]), media_type="audio/wav")

    return app


def _speak(record: dict) -> bytes:
    """The real read-back of the record, made on request and never stored."""
    from jatayu.models import Field, MedicationEntry
    from jatayu.readback import synthesize_entry

    f = lambda v: Field(value=v, span=None, confidence=1.0, source="user")  # noqa: E731
    e = MedicationEntry(drug=f(record["drug"]), dose_value=f(record["dose"]), dose_unit=f(record["unit"]),
                        route=f(record["route"]), time=f(datetime.now().astimezone()), flags=[])
    return synthesize_entry(e)


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Read-back test</title>
<style>
:root { --ink:#141210; --muted:#6b6863; --rule:#b9b5ad; --paper:#f6f4ef; --card:#ecebe5; }
* { box-sizing: border-box; }
body { margin: 0; font: 400 17px/1.5 system-ui, sans-serif; color: var(--ink); background: var(--paper); }
main { max-width: 640px; margin: 0 auto; padding: 32px 16px; }
h1 { font-size: 22px; margin: 0 0 16px; }
.card { background: var(--card); border: 1px solid var(--rule); border-radius: 14px; padding: 20px; margin: 16px 0; }
.label { font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
.drug { font: 600 32px/1.1 system-ui, sans-serif; text-transform: uppercase; margin: 2px 0 14px; }
.say { font-size: 24px; font-weight: 600; }
.fields { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.v { font-size: 19px; font-weight: 500; }
.row { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 16px; }
button { font: 500 17px system-ui, sans-serif; padding: 12px 20px; border-radius: 999px; border: 1px solid var(--ink);
         background: transparent; color: var(--ink); cursor: pointer; }
button.primary { background: var(--ink); color: var(--paper); }
button:disabled { opacity: .45; cursor: default; }
input { font: 400 19px system-ui, sans-serif; padding: 10px 12px; border-radius: 10px; border: 1px solid var(--rule); }
.muted { color: var(--muted); font-size: 14px; }
[hidden] { display: none !important; }
</style></head>
<body><main>
<h1>Read-back test</h1>
<section id="start">
  <p>You will be given medication orders to say aloud. After each one, the scribe shows and reads back what it
  recorded. Press <b>Confirm</b> if the record is what you said, or <b>Needs correction</b> if anything differs.</p>
  <p class="muted">Use the anonymous code you were given (for example T01), never your name. Nothing you say is
  recorded.</p>
  <div class="row"><input id="tid" aria-label="Tester code" placeholder="T01" autocomplete="off">
  <button class="primary" id="begin">Start</button></div>
  <p id="err" class="muted" role="alert"></p>
</section>
<section id="sayit" hidden>
  <div class="card"><div class="label">Say this aloud</div><div class="say" id="say"></div></div>
  <div class="row"><button class="primary" id="said">I said it</button></div>
</section>
<section id="confirm" hidden>
  <div class="card">
    <div class="label">Drug</div><div class="drug" id="drug"></div>
    <div class="fields">
      <div><div class="label">Dose</div><div class="v" id="dose"></div></div>
      <div><div class="label">Unit</div><div class="v" id="unit"></div></div>
      <div><div class="label">Route</div><div class="v" id="route"></div></div>
    </div>
  </div>
  <div class="row">
    <button id="replay">&#9654; Read back again</button>
    <button class="primary" id="ok" disabled>Confirm</button>
    <button id="fix" disabled>Needs correction</button>
  </div>
</section>
<section id="done" hidden><p>Finished. Thank you.</p></section>
<p class="muted">{{DISCLAIMER}} Synthetic records only.</p>
</main>
<script>
const $ = (id) => document.getElementById(id);
const show = (id) => ["start", "sayit", "confirm", "done"].forEach((s) => ($(s).hidden = s !== id));
const audio = new Audio();
let tester = "", trial = null, shownAt = 0;
async function post(path, body) {
  const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = await r.json();
  if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : "error");
  return j;
}
function render(state) {
  if (state.done) { show("done"); return; }
  trial = state.trial;
  $("say").textContent = trial.say;
  show("sayit");
}
function play() {
  $("ok").disabled = $("fix").disabled = true;
  audio.src = `/api/readback-test/audio/${tester}/${trial.token}`;
  const enable = () => { $("ok").disabled = $("fix").disabled = false; };
  audio.onended = enable; audio.onerror = enable;
  setTimeout(enable, 9000);
  audio.play().catch(enable);
}
$("begin").onclick = async () => {
  tester = $("tid").value.trim().toUpperCase();
  try { render(await post("/api/readback-test/session", { tester_id: tester })); $("err").textContent = ""; }
  catch (e) { $("err").textContent = e.message; }
};
$("said").onclick = () => {
  const r = trial.record;
  $("drug").textContent = r.drug;
  $("dose").textContent = r.dose;
  $("unit").textContent = `${r.unit} · ${r.unit_words}`;
  $("route").textContent = `${r.route} · ${r.route_words}`;
  show("confirm"); shownAt = performance.now(); play();
};
$("replay").onclick = play;
async function answer(a) {
  $("ok").disabled = $("fix").disabled = true;
  audio.pause();
  render(await post("/api/readback-test/answer",
    { tester_id: tester, token: trial.token, answer: a, ms: Math.round(performance.now() - shownAt) }));
}
$("ok").onclick = () => answer("confirm");
$("fix").onclick = () => answer("needs_correction");
</script></body></html>
"""

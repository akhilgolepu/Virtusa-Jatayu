"""Record-corpus API: prompts to read aloud, take uploads with an automatic ASR prompt check, and an
append-only manifest. Gold labels for an edited prompt are realigned, never silently kept stale."""
from __future__ import annotations

import copy
import json
import re
import threading
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from jatayu.audio import decode_to_16k
from jatayu.lexicon import Lexicon
from jatayu.textcompare import compare_tokens, normalised_wer

WER_OK = 0.40
GOLD_FIELDS = ("drug", "procedure", "dose_value", "dose_unit", "route", "detail", "measured_value")
CHECKED_FIELDS = ("drug", "procedure", "dose_value", "dose_unit", "route")  # must be heard as written


class Resolve(BaseModel):
    action: Literal["rerecord", "keep_edited"]
    gold_text: str | None = None


def realign(entries: list[dict], text: str) -> list[dict] | None:
    """Find each gold surface in `text`, left to right in span order. Returns entries with updated spans,
    or None if any surface is missing (the take then needs manual annotation)."""
    entries = copy.deepcopy(entries)
    fields = []
    for e in entries:
        fields += [e[n] for n in GOLD_FIELDS if e.get(n)]
        if e.get("time", {}).get("surface"):
            fields.append(e["time"])
    cursor = 0
    for f in sorted(fields, key=lambda f: f["span"][0]):
        # Whole tokens only: "1" must not realign into "10", nor unit "g" into "mg", nor "5" into "0.5".
        m = re.compile(r"(?<![\w.])" + re.escape(f["surface"]) + r"(?!\w)").search(text, cursor)
        if m is None:
            return None
        f["span"] = [m.start(), m.end()]
        cursor = m.end()
    return entries


def gold_field_mismatches(entries: list[dict], asr_text: str, lexicon: Lexicon) -> list[str]:
    """Gold fields whose (normalised) words are not heard in the take. A changed dose is one token of many,
    so it can pass the WER bar; this catches it so the take goes to review instead of keeping stale gold."""
    hyp = compare_tokens(asr_text, lexicon)
    missing = []
    for e in entries:
        for name in CHECKED_FIELDS:
            f = e.get(name)
            if not f:
                continue
            ref = compare_tokens(f["surface"], lexicon)
            if ref and not any(hyp[i:i + len(ref)] == ref for i in range(len(hyp) - len(ref) + 1)):
                missing.append(name)
    return missing


class CorpusStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.audio = self.root / "audio"
        self.manifest = self.root / "manifest.jsonl"
        self._lock = threading.Lock()

    def prompts(self) -> dict[str, dict]:
        path = self.root / "prompts.jsonl"
        if not path.exists():
            return {}
        return {p["prompt_id"]: p for p in map(json.loads, path.read_text("utf-8").splitlines()) if p}

    def rows(self) -> list[dict]:
        """Latest row per take_id, in first-recorded order."""
        if not self.manifest.exists():
            return []
        latest: dict[str, dict] = {}
        for line in self.manifest.read_text("utf-8").splitlines():
            if line:
                row = json.loads(line)
                latest[row["take_id"]] = row
        return list(latest.values())

    def append(self, row: dict) -> dict:
        with self._lock, open(self.manifest, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    def new_take_path(self, prompt_id: str) -> tuple[int, Path]:
        """Never overwrites: takes are numbered after every file already on disk for this prompt."""
        self.audio.mkdir(parents=True, exist_ok=True)
        take = len(list(self.audio.glob(f"{prompt_id}__*.wav"))) + 1
        while (path := self.audio / f"{prompt_id}__{take:02d}.wav").exists():
            take += 1
        return take, path

    def prompt_status(self) -> dict[str, str]:
        status = {pid: "todo" for pid in self.prompts()}
        for row in self.rows():
            status[row["prompt_id"]] = row["status"]
        return status


def create_corpus_router(recordings_dir: Path, transcriber, lexicon: Lexicon) -> APIRouter:
    store = CorpusStore(recordings_dir)
    router = APIRouter(prefix="/api/corpus")

    @router.get("/prompts")
    def list_prompts(status: Literal["todo", "review", "all"] = "all"):
        current = store.prompt_status()
        want = {"todo": {"todo", "rerecord"}, "review": {"review"}}.get(status)
        return [{**p, "status": current[pid]} for pid, p in store.prompts().items()
                if want is None or current[pid] in want]

    @router.post("/recordings")
    def upload(prompt_id: str = Form(...), condition: str = Form("unspecified"), audio: UploadFile = File(...)):
        prompt = store.prompts().get(prompt_id)
        if prompt is None:
            raise HTTPException(404, "unknown prompt")
        try:
            samples, wav = decode_to_16k(audio.file.read())
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        with store._lock:
            take, path = store.new_take_path(prompt_id)
            path.write_bytes(wav)
        row = {"take_id": uuid.uuid4().hex, "prompt_id": prompt_id, "take": take, "split": prompt.get("split"),
               "path": str(path.relative_to(store.root)), "condition": condition,
               "recorded_at": datetime.now().astimezone().isoformat(),
               "gold_text": prompt["text"], "entries": prompt["entries"]}
        if prompt.get("split") == "test":
            # Sealed: a test take is never transcribed at record time (that would be a speech result on test).
            # The reader checks their own take by listening; the evaluator releases test clips.
            return store.append({**row, "asr_text": None, "wer": None, "gold_field_mismatch": [], "status": "sealed"})
        asr_text = transcriber.transcribe(samples).text
        wer = normalised_wer(prompt["text"], asr_text, lexicon)
        mismatch = gold_field_mismatches(prompt["entries"], asr_text, lexicon)
        return store.append({**row, "asr_text": asr_text, "wer": round(wer, 4), "gold_field_mismatch": mismatch,
                             "status": "ok" if wer <= WER_OK and not mismatch else "review"})

    @router.post("/recordings/{take_id}/resolve")
    def resolve(take_id: str, body: Resolve):
        row = next((r for r in store.rows() if r["take_id"] == take_id), None)
        if row is None:
            raise HTTPException(404, "unknown take")
        row = {**row, "resolved_at": datetime.now().astimezone().isoformat()}
        if body.action == "rerecord":
            row["status"] = "rerecord"
        else:
            if not body.gold_text or not body.gold_text.strip():
                raise HTTPException(422, "gold_text required for keep_edited")
            aligned = realign(row["entries"], body.gold_text)
            row["gold_text"] = body.gold_text
            row["status"] = "keep_edited" if aligned is not None else "needs_annotation"
            row["entries"] = aligned if aligned is not None else row["entries"]
        return store.append(row)

    @router.get("/stats")
    def stats():
        rows = store.rows()
        return {"prompts": len(store.prompts()), "takes": len(rows),
                "by_status": Counter(store.prompt_status().values()),
                "by_condition": Counter(r["condition"] for r in rows)}

    return router

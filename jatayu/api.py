"""FastAPI app: incidents, utterances (text or audio), audit log + verify, and the throwaway capture page."""
from __future__ import annotations

import threading
from dataclasses import asdict
from importlib import resources
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from jatayu import config
from jatayu.asr import Transcriber
from jatayu.audit import AuditLog
from jatayu.corpus import create_corpus_router
from jatayu.extract.hybrid import HybridExtractor
from jatayu.extract.llm import LlmExtractor
from jatayu.extract.rules import RulesExtractor
from jatayu.llm import LlmError, LlmRunner
from jatayu.models_manager import ModelManager
from jatayu.device import device_id
from jatayu.incident import ENTRY, IncidentStore, apply_user_edit, incident_state
from jatayu.output.fhir import to_incident_bundle, validate_bundle
from jatayu.output.pdf import render_note
from jatayu.lexicon import Lexicon
from jatayu.pipeline import Pipeline, PipelineResult
from jatayu.readback import readback_text, synthesize_entry
from jatayu.validate import validate_all


class IncidentIn(BaseModel):
    label: str | None = None


class EditIn(BaseModel):
    entry: dict


class RejectIn(BaseModel):
    reason: str | None = None


class ConfirmIn(BaseModel):
    entry_ids: list[str]
    acknowledged: list[str] = []
    expected: dict[str, int] = {}  # entry_id -> history seq the medic was looking at


def _state_json(inc: dict, state) -> dict:
    return {**inc, "utterances": state.utterances,
            "entries": [{"entry": s.entry.model_dump(mode="json"), "status": s.status, "history": s.history,
                         "utterance_id": s.utterance_id, "acknowledged": s.acknowledged}
                        for s in state.entries.values()]}


class ManagedTranscriber:
    """Routes ASR through the ModelManager so that, in swap mode, the LLM is unloaded before Whisper runs."""

    def __init__(self, inner: Transcriber, manager: ModelManager):
        self.inner, self.manager = inner, manager

    @property
    def device(self) -> str:
        return self.inner.device

    def transcribe(self, samples):
        return self.manager.get("asr").transcribe(samples)


def create_app(db_path: Path = config.DB_PATH, transcriber: Transcriber | None = None,
               audio_dir: Path = config.AUDIO_DIR, recordings_dir: Path = config.DATA_DIR / "recordings") -> FastAPI:
    lexicon = Lexicon.load()
    audit = AuditLog(db_path)
    transcriber = transcriber or Transcriber(lexicon=lexicon)  # model loads lazily on first audio request
    runner = LlmRunner(config.LLM_MODEL_PATH)
    manager = ModelManager({"asr": lambda: transcriber, "llm": lambda: runner},
                           {"asr": lambda t: t.unload(), "llm": lambda r: r.close()}, keep_all=config.KEEP_MODELS)
    llm = lambda: manager.get("llm")  # noqa: E731
    rules = RulesExtractor(lexicon)
    extractors = {"rules": rules, "hybrid": HybridExtractor(lexicon, llm, rules)}
    if config.EXPERIMENTAL:  # LLM-only: experimental, off the demo path (round 9)
        extractors["llm"] = LlmExtractor(lexicon, llm)
    asr = ManagedTranscriber(transcriber, manager) if hasattr(transcriber, "unload") else transcriber
    pipeline = Pipeline(lexicon, extractors[config.DEFAULT_EXTRACTOR], audit, asr, audio_dir=audio_dir,
                        validator=lambda entries, history: validate_all(entries, lexicon, history))
    incidents = IncidentStore(db_path)
    write_lock = threading.Lock()  # check-then-append for edit/confirm must not interleave
    device = device_id(Path(db_path).parent)

    def _incident(incident_id: str) -> dict:
        inc = incidents.get(incident_id)
        if inc is None:
            raise HTTPException(404, "unknown incident")
        return inc

    app = FastAPI(title="Jatayu", description=config.DISCLAIMER)
    app.include_router(create_corpus_router(recordings_dir, transcriber, lexicon))

    @app.get("/api/health")
    def health():
        return {"ok": True, "asr_device": transcriber.device, "offline": True, "device_id": device,
                "extractors": list(extractors), "default_extractor": config.DEFAULT_EXTRACTOR,
                "experimental": [x for x in extractors if x in config.EXPERIMENTAL_EXTRACTORS]}

    @app.post("/api/incidents")
    def create_incident(body: IncidentIn):
        return incidents.create(body.label)

    @app.get("/api/incidents")
    def list_incidents():
        return incidents.list()

    @app.get("/api/incidents/{incident_id}")
    def get_incident(incident_id: str):
        inc = _incident(incident_id)
        return _state_json(inc, incident_state(audit, incident_id))

    @app.post("/api/utterances", response_model=PipelineResult)
    def create_utterance(incident_id: str = Form(...), text: str | None = Form(None),
                         audio: UploadFile | None = File(None), extractor: str = Form(config.DEFAULT_EXTRACTOR)):
        _incident(incident_id)
        if audio is None and (text is None or not text.strip()):
            raise HTTPException(422, "give text or audio")
        if extractor in config.EXPERIMENTAL_EXTRACTORS and extractor not in extractors:
            raise HTTPException(403, f"{extractor!r} (LLM-only) is experimental and off in the demo; "
                                     "set JATAYU_EXPERIMENTAL=1 to use it")
        if extractor not in extractors:
            raise HTTPException(422, f"unknown extractor {extractor!r}; choose from {sorted(extractors)}")
        history = incident_state(audit, incident_id).current_entries()
        kwargs = {"extractor": extractors[extractor], "history": history}
        try:
            if audio is not None:
                return pipeline.run(incident_id, audio=audio.file.read(), **kwargs)
            return pipeline.run(incident_id, text=text, **kwargs)
        except LlmError as exc:
            raise HTTPException(503, f"LLM unavailable: {exc}") from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/api/incidents/{incident_id}/entries/{entry_id}/edit")
    def edit_entry(incident_id: str, entry_id: str, body: EditIn):
        _incident(incident_id)
        state = incident_state(audit, incident_id)
        current = state.entries.get(entry_id)
        if current is None:
            raise HTTPException(404, "unknown entry")
        try:
            edited = ENTRY.validate_python({**body.entry, "id": entry_id, "kind": current.entry.kind})
        except Exception as exc:
            raise HTTPException(422, f"invalid entry: {exc}") from exc
        entry = apply_user_edit(current.entry, edited)
        if pipeline.validator is not None:
            others = [e for e in state.current_entries() if e.id != entry_id]
            entry = pipeline.validator([entry], others)[0]
        row = audit.append("edit", incident_id, {"type": "edit", "entry_id": entry_id,
                                                 "entry": entry.model_dump(mode="json")},
                           supersedes_seq=current.history[-1])
        return {"seq": row.seq, "entry": entry.model_dump(mode="json")}

    @app.post("/api/incidents/{incident_id}/confirm")
    def confirm(incident_id: str, body: ConfirmIn):
        _incident(incident_id)
        with write_lock:
            return _confirm(incident_id, body)

    def _confirm(incident_id: str, body: ConfirmIn):
        state = incident_state(audit, incident_id)
        missing = [eid for eid in body.entry_ids if eid not in state.entries]
        if missing or not body.entry_ids:
            raise HTTPException(404, f"unknown entries: {missing}")
        rejected = [eid for eid in body.entry_ids if state.entries[eid].status == "rejected"]
        if rejected:
            raise HTTPException(409, {"rejected": rejected, "message": "a rejected entry cannot be confirmed"})
        stale = [eid for eid, seq in body.expected.items() if eid in state.entries and state.entries[eid].history[-1] != seq]
        if stale:  # the entry changed since the medic looked at it: confirm what they saw, or nothing
            raise HTTPException(409, {"stale": stale, "message": "entry changed since it was displayed; reload"})
        needs_dose = [eid for eid in body.entry_ids
                      if any(f.code == "concentration_not_dose" for f in state.entries[eid].entry.flags)]
        if needs_dose:  # a concentration was said, not a dose: the responder must enter the dose (edit) first
            raise HTTPException(409, {"needs_dose": needs_dose,
                                      "message": "a concentration was recorded, not a dose: enter the dose given"})
        unack = [{"entry_id": eid, "code": f.code, "message": f.message}
                 for eid in body.entry_ids for f in state.entries[eid].entry.flags
                 if f.severity == "high" and f.code not in body.acknowledged]
        if unack:  # nothing is written: high flags must be acknowledged explicitly
            raise HTTPException(409, {"unacknowledged": unack})
        seen = {eid: state.entries[eid].history[-1] for eid in body.entry_ids}
        row = audit.append("confirm", incident_id, {"type": "confirm", "entry_ids": body.entry_ids,
                                                    "acknowledged": body.acknowledged, "confirmed_versions": seen})
        return {"seq": row.seq}

    def _entry(incident_id: str, entry_id: str):
        _incident(incident_id)
        s = incident_state(audit, incident_id).entries.get(entry_id)
        if s is None:
            raise HTTPException(404, "unknown entry")
        return s.entry

    @app.get("/api/incidents/{incident_id}/entries/{entry_id}/readback.txt", response_class=PlainTextResponse)
    def readback_txt(incident_id: str, entry_id: str):
        return readback_text(_entry(incident_id, entry_id))

    @app.get("/api/incidents/{incident_id}/entries/{entry_id}/readback.wav")
    def readback_wav(incident_id: str, entry_id: str):
        return Response(synthesize_entry(_entry(incident_id, entry_id)), media_type="audio/wav")

    @app.post("/api/incidents/{incident_id}/entries/{entry_id}/reject")
    def reject_entry(incident_id: str, entry_id: str, body: RejectIn):
        _incident(incident_id)
        with write_lock:
            current = incident_state(audit, incident_id).entries.get(entry_id)
            if current is None:
                raise HTTPException(404, "unknown entry")
            row = audit.append("edit", incident_id, {"type": "reject", "entry_id": entry_id, "reason": body.reason},
                               supersedes_seq=current.history[-1])
        return {"seq": row.seq}

    def _bundle(incident_id: str) -> dict:
        """The incident's FHIR-lite bundle, schema-validated. The JSON endpoint and the PDF both use this one."""
        inc = _incident(incident_id)
        state = incident_state(audit, incident_id)
        items = [(s.entry, s.status, s.utterance_id) for s in state.entries.values()]
        bundle = to_incident_bundle({**inc, "device": device}, items, state.utterances, lexicon)
        validate_bundle(bundle)
        return bundle

    @app.get("/api/incidents/{incident_id}/note.pdf")
    def incident_pdf(incident_id: str):
        inc = _incident(incident_id)
        pdf = render_note({**inc, "device": device}, _bundle(incident_id), audit.rows(incident_id), audit.verify())
        return Response(pdf, media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="jatayu-{incident_id[:8]}.pdf"'})

    @app.get("/api/incidents/{incident_id}/bundle")
    def incident_bundle(incident_id: str):
        return _bundle(incident_id)

    @app.get("/api/audit")
    def audit_rows(incident_id: str | None = None):
        return [asdict(r) for r in audit.rows(incident_id)]

    @app.get("/api/audit/verify")
    def audit_verify():
        return asdict(audit.verify())

    @app.get("/api/lexicon")
    def lexicon_json():
        return {"drugs": [{"name": n, "aliases": lexicon.drug(n).aliases, "routes": lexicon.drug(n).routes,
                           "units": lexicon.drug(n).units} for n in lexicon.drug_names()],
                "procedures": lexicon.procedure_names(), "routes": lexicon.route_codes(),
                "units": lexicon.unit_codes()}

    @app.get("/skeleton", response_class=HTMLResponse)
    def skeleton_page():
        return resources.files("jatayu.web").joinpath("skeleton.html").read_text("utf-8")

    # The DOT-styled single-page app (built by `npm run build` in web/, committed so no Node is needed to run).
    dist = Path(__file__).resolve().parent / "web" / "dist"
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", response_class=HTMLResponse, include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "not found")
        index = dist / "index.html"
        if index.exists():
            return FileResponse(index, media_type="text/html")
        return resources.files("jatayu.web").joinpath("skeleton.html").read_text("utf-8")

    return app


app = create_app()

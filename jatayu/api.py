"""FastAPI app: incidents, utterances (text or audio), audit log + verify, and the throwaway capture page."""
from __future__ import annotations

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
from jatayu.incident import ENTRY, IncidentStore, apply_user_edit, incident_state
from jatayu.output.fhir import to_incident_bundle, validate_bundle
from jatayu.output.pdf import render_note
from jatayu.lexicon import Lexicon
from jatayu.pipeline import Pipeline, PipelineResult
from jatayu.readback import readback_text, synthesize_readback
from jatayu.validate import validate_all


class IncidentIn(BaseModel):
    label: str | None = None


class EditIn(BaseModel):
    entry: dict


class ConfirmIn(BaseModel):
    entry_ids: list[str]
    acknowledged: list[str] = []


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
    extractors = {"rules": rules, "llm": LlmExtractor(lexicon, llm), "hybrid": HybridExtractor(lexicon, llm, rules)}
    asr = ManagedTranscriber(transcriber, manager) if hasattr(transcriber, "unload") else transcriber
    pipeline = Pipeline(lexicon, extractors[config.DEFAULT_EXTRACTOR], audit, asr, audio_dir=audio_dir,
                        validator=lambda entries, history: validate_all(entries, lexicon, history))
    incidents = IncidentStore(db_path)

    def _incident(incident_id: str) -> dict:
        inc = incidents.get(incident_id)
        if inc is None:
            raise HTTPException(404, "unknown incident")
        return inc

    app = FastAPI(title="Jatayu", description=config.DISCLAIMER)
    app.include_router(create_corpus_router(recordings_dir, transcriber, lexicon))

    @app.get("/api/health")
    def health():
        return {"ok": True, "asr_device": transcriber.device, "offline": True}

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
        state = incident_state(audit, incident_id)
        missing = [eid for eid in body.entry_ids if eid not in state.entries]
        if missing or not body.entry_ids:
            raise HTTPException(404, f"unknown entries: {missing}")
        unack = [{"entry_id": eid, "code": f.code, "message": f.message}
                 for eid in body.entry_ids for f in state.entries[eid].entry.flags
                 if f.severity == "high" and f.code not in body.acknowledged]
        if unack:  # nothing is written: high flags must be acknowledged explicitly
            raise HTTPException(409, {"unacknowledged": unack})
        row = audit.append("confirm", incident_id, {"type": "confirm", "entry_ids": body.entry_ids,
                                                    "acknowledged": body.acknowledged})
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
        return Response(synthesize_readback(readback_text(_entry(incident_id, entry_id))), media_type="audio/wav")

    @app.get("/api/incidents/{incident_id}/note.pdf")
    def incident_pdf(incident_id: str):
        inc = _incident(incident_id)
        pdf = render_note(inc, incident_state(audit, incident_id), audit.rows(incident_id), audit.verify())
        return Response(pdf, media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="jatayu-{incident_id[:8]}.pdf"'})

    @app.get("/api/incidents/{incident_id}/bundle")
    def incident_bundle(incident_id: str):
        inc = _incident(incident_id)
        state = incident_state(audit, incident_id)
        items = [(s.entry, s.status, s.utterance_id) for s in state.entries.values()]
        bundle = to_incident_bundle(inc, items, state.utterances, lexicon)
        validate_bundle(bundle)
        return bundle

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

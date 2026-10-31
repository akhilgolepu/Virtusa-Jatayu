"""FastAPI app: incidents, utterances (text or audio), audit log + verify, and the throwaway capture page."""
from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import datetime
from importlib import resources
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from jatayu import config
from jatayu.asr import Transcriber
from jatayu.audit import AuditLog
from jatayu.extract.rules import RulesExtractor
from jatayu.lexicon import Lexicon
from jatayu.pipeline import Pipeline, PipelineResult


class IncidentIn(BaseModel):
    label: str | None = None


def create_app(db_path: Path = config.DB_PATH, transcriber: Transcriber | None = None,
               audio_dir: Path = config.AUDIO_DIR) -> FastAPI:
    lexicon = Lexicon.load()
    audit = AuditLog(db_path)
    transcriber = transcriber or Transcriber(lexicon=lexicon)  # model loads lazily on first audio request
    pipeline = Pipeline(lexicon, RulesExtractor(lexicon), audit, transcriber, audio_dir=audio_dir)
    incidents: dict[str, dict] = {}  # Phase 1: in memory; Plan 3 persists incidents

    app = FastAPI(title="Jatayu", description=config.DISCLAIMER)

    @app.get("/api/health")
    def health():
        return {"ok": True, "asr_device": transcriber.device, "offline": True}

    @app.post("/api/incidents")
    def create_incident(body: IncidentIn):
        inc = {"id": uuid.uuid4().hex, "label": body.label, "started_at": datetime.now().astimezone().isoformat()}
        incidents[inc["id"]] = inc
        return inc

    @app.post("/api/utterances", response_model=PipelineResult)
    def create_utterance(incident_id: str = Form(...), text: str | None = Form(None),
                         audio: UploadFile | None = File(None)):
        if incident_id not in incidents:
            raise HTTPException(404, "unknown incident")
        if audio is None and (text is None or not text.strip()):
            raise HTTPException(422, "give text or audio")
        try:
            if audio is not None:
                return pipeline.run(incident_id, audio=audio.file.read())
            return pipeline.run(incident_id, text=text)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/audit")
    def audit_rows(incident_id: str | None = None):
        return [asdict(r) for r in audit.rows(incident_id)]

    @app.get("/api/audit/verify")
    def audit_verify():
        return asdict(audit.verify())

    @app.get("/", response_class=HTMLResponse)
    def page():
        return resources.files("jatayu.web").joinpath("skeleton.html").read_text("utf-8")

    return app


app = create_app()

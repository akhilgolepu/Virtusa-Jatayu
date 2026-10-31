"""capture -> ASR -> extract -> FHIR-lite -> audit draft row."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from jatayu import config
from jatayu.asr import Transcriber
from jatayu.audio import decode_to_16k
from jatayu.audit import AuditLog, sha256_hex
from jatayu.extract.base import Extractor
from jatayu.lexicon import Lexicon
from jatayu.models import Entry, Utterance
from jatayu.output.fhir import to_bundle, validate_bundle

NO_SPEECH = "no speech detected"


class PipelineResult(BaseModel):
    utterance: Utterance
    entries: list[Entry]
    bundle: dict
    audit_seq: int
    asr: dict | None = None
    warnings: list[str] = []


class Pipeline:
    def __init__(self, lexicon: Lexicon, extractor: Extractor, audit: AuditLog,
                 transcriber: Transcriber | None = None, audio_dir: Path = config.AUDIO_DIR):
        self.lexicon = lexicon
        self.extractor = extractor
        self.audit = audit
        self.transcriber = transcriber
        self.audio_dir = Path(audio_dir)

    def run(self, incident_id: str, *, text: str | None = None, audio: bytes | None = None,
            capture_time: datetime | None = None) -> PipelineResult:
        if (text is None) == (audio is None):
            raise ValueError("give exactly one of text or audio")
        capture_time = capture_time or datetime.now().astimezone()

        audio_sha = audio_path = asr = None
        if audio is not None:
            if self.transcriber is None:
                raise ValueError("audio given but no transcriber configured")
            samples, wav = decode_to_16k(audio)
            audio_sha = sha256_hex(wav)
            self.audio_dir.mkdir(parents=True, exist_ok=True)
            path = self.audio_dir / f"{audio_sha}.wav"
            path.write_bytes(wav)
            audio_path = str(path)
            result = self.transcriber.transcribe(samples)
            text, asr = result.text, result.as_dict()

        utterance = Utterance(incident_id=incident_id, capture_time=capture_time, raw_transcript=text,
                              audio_sha256=audio_sha, audio_path=audio_path)
        warnings = []
        if text.strip():
            entries = self.extractor.extract(text, capture_time)
        else:
            entries = []
            warnings.append(NO_SPEECH)

        bundle = to_bundle(utterance, entries, self.lexicon)
        validate_bundle(bundle)
        row = self.audit.append("draft", incident_id, bundle, transcript=text, audio_sha256=audio_sha)
        return PipelineResult(utterance=utterance, entries=entries, bundle=bundle, audit_seq=row.seq,
                              asr=asr, warnings=warnings)

"""Readable PDF note for an incident (Mecha-ledger style: hairline rules, small caps labels, numbered rows)."""
from __future__ import annotations

import io
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from jatayu.audit import AuditRow, VerifyResult
from jatayu.config import DISCLAIMER
from jatayu.output.fhir import clinical, provenance, status_reason, transcripts

INK = colors.HexColor("#141210")
MUTED = colors.HexColor("#6b6863")
RULE = colors.HexColor("#b9b5ad")
ALERT = colors.HexColor("#da291c")

LABEL = ParagraphStyle("label", fontName="Helvetica", fontSize=6.5, leading=8, textColor=MUTED)
BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=8.5, leading=11, textColor=INK)
TITLE = ParagraphStyle("title", fontName="Helvetica", fontSize=20, leading=24, textColor=INK)
MONO = ParagraphStyle("mono", fontName="Courier", fontSize=7.5, leading=9.5, textColor=INK)


def _label(text: str) -> Paragraph:
    return Paragraph(text.upper().replace(" ", "&nbsp;"), LABEL)


def _t(dt) -> str:
    return (dt if isinstance(dt, datetime) else datetime.fromisoformat(str(dt))).strftime("%H:%M")


def _ledger(rows: list[list], widths: list[float]) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, INK),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
    ]))
    return table


def _letters(s: str) -> str:
    return "".join(c for c in s.lower() if c.isalpha())


def _entry_row(n: int, res: dict) -> list:
    """One table row, read from a FHIR-lite resource of the validated bundle (the PDF has no other source)."""
    prov = provenance(res)
    if res["resourceType"] == "MedicationAdministration":
        item = escape(res["medicationCodeableConcept"]["text"])
        heard = (prov.get("drug") or {}).get("raw")
        if heard and _letters(heard) != _letters(res["medicationCodeableConcept"]["text"]):
            item += f'<br/><font size="7" color="#6b6863">heard “{escape(heard)}”</font>'  # never hidden (round 9)
        d = res.get("dosage", {})
        dose = f"{d['dose']['value']:g} {d['dose'].get('unit', '?')}" if "dose" in d else "—"
        route = d.get("route", {}).get("text", "—")
        when = res["effectiveDateTime"]
    else:
        item = escape(res["code"]["text"] + "".join(f" ({n['text']})" for n in res.get("note", [])))
        dose, route = "", ""
        when = res["performedDateTime"]
    flags = "<br/>".join(f'<font color="#da291c">&#9650;</font> {f["code"]}' if f["severity"] == "high" else f"&#9651; {f['code']}"
                         for f in prov["flags"]) or "—"
    review = prov.get("review_status", "draft")
    status_text = f"<b>{review.upper()}</b>"
    if res["status"] == "not-done":  # never shown as an administration (see output/fhir.py NOT_DONE)
        what = "READING" if (status_reason(res) or "").startswith("A reading") else "NOT GIVEN"
        status_text = f'<font color="#da291c"><b>{what}</b></font><br/>{review}'
    return [Paragraph(f"{n:02d}", MONO), Paragraph(_t(when), MONO), Paragraph(item, BODY),
            Paragraph(dose, BODY), Paragraph(route, BODY), Paragraph(status_text, BODY), Paragraph(flags, BODY)]


def render_note(incident: dict, bundle: dict, rows: list[AuditRow], verify: VerifyResult) -> bytes:
    """The PDF note. Entries come from the FHIR-lite bundle (already schema-validated by the caller), so the PDF and
    the JSON cannot disagree; the record history and chain verdict come from the audit log."""
    buf = io.BytesIO()

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 10 * mm, DISCLAIMER)
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Scribe108 · page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=18 * mm, title=f"Scribe108 note {incident['id'][:8]}", author="Scribe108")
    story: list = [_label("Incident note"), Paragraph(incident.get("label") or "Unlabelled incident", TITLE),
                   Paragraph(f"Started {datetime.fromisoformat(incident['started_at']).strftime('%d %b %Y, %H:%M')}"
                             f" · {len(clinical(bundle))} entries · {len(transcripts(bundle))} utterances", BODY),
                   Paragraph(f"Incident {incident['id']} · Device {incident.get('device', 'unknown')}", MONO),
                   Spacer(1, 6 * mm), _label("Entries")]
    head = [_label(h) for h in ("#", "Time", "Drug / procedure", "Dose", "Route", "Status", "Flags")]
    entries = [_entry_row(i + 1, res) for i, res in enumerate(clinical(bundle))]
    story += [_ledger([head, *entries], [8 * mm, 12 * mm, 44 * mm, 22 * mm, 14 * mm, 22 * mm, 52 * mm]),
              Spacer(1, 6 * mm), _label("Record history (append-only)")]
    hist_head = [_label(h) for h in ("Seq", "Event", "Time", "Entry hash")]
    hist = [[Paragraph(str(r.seq), MONO), Paragraph(r.event_type, BODY), Paragraph(_t(r.ts), MONO),
             Paragraph(r.entry_hash[:24] + "…", MONO)] for r in rows]
    story += [_ledger([hist_head, *hist], [12 * mm, 24 * mm, 16 * mm, 70 * mm]), Spacer(1, 6 * mm),
              _label("Audit chain")]
    head_hash = rows[-1].entry_hash if rows else "—"
    verdict = (f"Chain verified: {verify.checked} rows intact." if verify.ok else
               f'<font color="#da291c"><b>CHAIN BROKEN at seq {verify.first_bad_seq}: {verify.reason}</b></font>')
    story += [Paragraph(verdict, BODY), Paragraph(f"Head hash {head_hash}", MONO)]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()

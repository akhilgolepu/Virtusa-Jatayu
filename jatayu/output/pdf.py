"""Readable PDF note for an incident (Mecha-ledger style: hairline rules, small caps labels, numbered rows)."""
from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from jatayu.audit import AuditRow, VerifyResult
from jatayu.config import DISCLAIMER
from jatayu.incident import IncidentState
from jatayu.models import MedicationEntry

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


def _entry_row(n: int, entry, status: str) -> list:
    if isinstance(entry, MedicationEntry):
        item = entry.drug.value or "—"
        dose = "—" if entry.dose_value.value is None else f"{entry.dose_value.value:g} {entry.dose_unit.value or '?'}"
        route = entry.route.value or "—"
    else:
        item = entry.procedure.value + (f" ({entry.detail.value})" if entry.detail and entry.detail.value else "")
        dose, route = "", ""
    flags = "<br/>".join(f'<font color="#da291c">&#9650;</font> {f.code}' if f.severity == "high" else f"&#9651; {f.code}"
                         for f in entry.flags) or "—"
    status_text = f"<b>{status.upper()}</b>"
    codes = {f.code for f in entry.flags}
    if status != "rejected" and codes & {"possible_not_given", "possible_measurement"}:
        # never shown as an administration (see output/fhir.py NOT_DONE)
        what = "NOT GIVEN" if "possible_not_given" in codes else "READING"
        status_text = f'<font color="#da291c"><b>{what}</b></font><br/>{status}'
    return [Paragraph(f"{n:02d}", MONO), Paragraph(_t(entry.time.value), MONO), Paragraph(item, BODY),
            Paragraph(dose, BODY), Paragraph(route, BODY), Paragraph(status_text, BODY), Paragraph(flags, BODY)]


def render_note(incident: dict, state: IncidentState, rows: list[AuditRow], verify: VerifyResult) -> bytes:
    buf = io.BytesIO()

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 10 * mm, DISCLAIMER)
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Jatayu · page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=18 * mm, title=f"Jatayu note {incident['id'][:8]}", author="Jatayu")
    story: list = [_label("Incident note"), Paragraph(incident.get("label") or "Unlabelled incident", TITLE),
                   Paragraph(f"Started {datetime.fromisoformat(incident['started_at']).strftime('%d %b %Y, %H:%M')}"
                             f" · {len(state.entries)} entries · {len(state.utterances)} utterances", BODY),
                   Paragraph(f"Incident {incident['id']} · Device {incident.get('device', 'unknown')}", MONO),
                   Spacer(1, 6 * mm), _label("Entries")]
    head = [_label(h) for h in ("#", "Time", "Drug / procedure", "Dose", "Route", "Status", "Flags")]
    entries = [_entry_row(i + 1, s.entry, s.status) for i, s in enumerate(state.entries.values())]
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

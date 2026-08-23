import io
import logging
from datetime import datetime, timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

from app.models.job import Job

logger = logging.getLogger(__name__)


def generate_job_report_pdf(job: Job) -> bytes:
    """Render a PDF report from a completed job's structured intelligence result."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=25 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="SectionHeading",
        parent=styles["Heading2"],
        spaceBefore=12,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="BulletItem",
        parent=styles["Normal"],
        leftIndent=12,
        bulletIndent=0,
        spaceBefore=2,
        spaceAfter=2,
    ))

    elements = []

    # Title
    elements.append(Paragraph("ClarityAI — Meeting Intelligence Report", styles["Title"]))
    elements.append(Spacer(1, 6 * mm))

    # Job metadata
    created_str = ""
    if job.created_at:
        if hasattr(job.created_at, "strftime"):
            created_str = job.created_at.strftime("%Y-%m-%d %H:%M UTC")
        else:
            created_str = str(job.created_at)

    elements.append(Paragraph(f"<b>Job ID:</b> {job.id}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Created:</b> {created_str}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Input Type:</b> {job.input_type}", styles["Normal"]))
    elements.append(Spacer(1, 6 * mm))

    # Extract ai_analysis from result
    result = job.result or {}
    analysis = result.get("ai_analysis", {}) or {}

    # Summary
    elements.append(Paragraph("Executive Summary", styles["SectionHeading"]))
    summary = analysis.get("summary", "")
    elements.append(Paragraph(summary or "No summary available.", styles["Normal"]))
    elements.append(Spacer(1, 4 * mm))

    # Key Points
    elements.append(Paragraph("Key Points", styles["SectionHeading"]))
    key_points = analysis.get("key_points", []) or []
    if key_points:
        for point in key_points:
            elements.append(Paragraph(f"• {_escape(point)}", styles["BulletItem"]))
    else:
        elements.append(Paragraph("None identified.", styles["Normal"]))
    elements.append(Spacer(1, 4 * mm))

    # Decisions
    elements.append(Paragraph("Decisions", styles["SectionHeading"]))
    decisions = analysis.get("decisions", []) or []
    if decisions:
        for d in decisions:
            decision_text = d.get("decision", "") if isinstance(d, dict) else str(d)
            rationale = d.get("rationale", "") if isinstance(d, dict) else ""
            line = f"• {_escape(decision_text)}"
            if rationale:
                line += f" — <i>Rationale: {_escape(rationale)}</i>"
            elements.append(Paragraph(line, styles["BulletItem"]))
    else:
        elements.append(Paragraph("None identified.", styles["Normal"]))
    elements.append(Spacer(1, 4 * mm))

    # Action Items
    elements.append(Paragraph("Action Items", styles["SectionHeading"]))
    action_items = analysis.get("action_items", []) or []
    if action_items:
        for a in action_items:
            task = a.get("task", "") if isinstance(a, dict) else str(a)
            owner = a.get("owner", "") if isinstance(a, dict) else ""
            line = f"• {_escape(task)}"
            if owner:
                line += f" — <i>Owner: {_escape(owner)}</i>"
            elements.append(Paragraph(line, styles["BulletItem"]))
    else:
        elements.append(Paragraph("None identified.", styles["Normal"]))
    elements.append(Spacer(1, 4 * mm))

    # Risks
    elements.append(Paragraph("Risks", styles["SectionHeading"]))
    risks = analysis.get("risks", []) or []
    if risks:
        for r in risks:
            desc = r.get("description", "") if isinstance(r, dict) else str(r)
            severity = r.get("severity", "") if isinstance(r, dict) else ""
            line = f"• {_escape(desc)}"
            if severity:
                line += f" — <i>Severity: {_escape(severity)}</i>"
            elements.append(Paragraph(line, styles["BulletItem"]))
    else:
        elements.append(Paragraph("None identified.", styles["Normal"]))
    elements.append(Spacer(1, 4 * mm))

    # Open Questions
    elements.append(Paragraph("Open Questions", styles["SectionHeading"]))
    open_questions = analysis.get("open_questions", []) or []
    if open_questions:
        for q in open_questions:
            question = q.get("question", "") if isinstance(q, dict) else str(q)
            owner = q.get("owner", "") if isinstance(q, dict) else ""
            line = f"• {_escape(question)}"
            if owner:
                line += f" — <i>Owner: {_escape(owner)}</i>"
            elements.append(Paragraph(line, styles["BulletItem"]))
    else:
        elements.append(Paragraph("None identified.", styles["Normal"]))
    elements.append(Spacer(1, 4 * mm))

    # Sentiment
    elements.append(Paragraph("Sentiment", styles["SectionHeading"]))
    sentiment = analysis.get("sentiment", "")
    elements.append(Paragraph(sentiment.capitalize() if sentiment else "Not available.", styles["Normal"]))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    logger.info("pdf_report_generated: job_id=%s bytes=%d", job.id, len(pdf_bytes))
    return pdf_bytes


def _escape(text: str) -> str:
    """Escape XML special characters for reportlab Paragraph."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

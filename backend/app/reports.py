from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak


def build_pdf(workspace, audit, findings, documents) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=letter, title="RAG Document Audit Report")
    styles = getSampleStyleSheet()
    story = [Paragraph("RAG DOCUMENT AUDIT REPORT", styles["Title"]), Spacer(1, 12)]
    story += [Paragraph(f"Workspace: {workspace.name}", styles["Normal"]), Paragraph(f"Audit date: {audit.created_at.isoformat()}", styles["Normal"]), Paragraph(f"AI Audit Health Score: {audit.health_score or 'N/A'} / 100", styles["Heading2"]), Spacer(1, 10)]
    story += [Paragraph("Documents analyzed", styles["Heading2"])]
    for item in documents:
        story.append(Paragraph(f"• {item.filename} ({item.status.value})", styles["Normal"]))
    story += [Spacer(1, 12), Paragraph(f"Findings summary: {len(findings)} findings", styles["Heading2"])]
    for finding in findings:
        story += [Paragraph(f"{finding.severity.value} — {finding.title}", styles["Heading3"]), Paragraph(finding.description, styles["Normal"]), Paragraph(f"AI confidence: {round(finding.confidence * 100)}%", styles["Normal"]), Paragraph(f"Recommendation: {finding.recommendation}", styles["Normal"])]
        for source in finding.sources:
            story.append(Paragraph(f"Evidence: {source.quoted_text}", styles["Code"]))
        story.append(Spacer(1, 8))
    story += [PageBreak(), Paragraph("Audit limitations", styles["Heading2"]), Paragraph("This report is AI-assisted analysis, not legal, financial, medical, compliance, or professional advice. Verify all findings against original documents and applicable authoritative sources.", styles["Normal"])]
    document.build(story)
    return buffer.getvalue()


import re
from pathlib import Path

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from app.config import OUTPUT_DIR

def safe_filename(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_")
    return cleaned or "certificate"

def generate_certificate(job_id: int, cert_id: int, name: str,
                         event_name: str, issued_by: str, issue_date: str) -> str:
    job_dir = Path(OUTPUT_DIR) / f"job_{job_id}"
    job_dir.mkdir(parents=True, exist_ok=True)

    file_path = job_dir / f"{cert_id}_{safe_filename(name)}.pdf"

    width, height = landscape(A4)
    pdf = canvas.Canvas(str(file_path), pagesize=(width, height))

    # Border
    pdf.setLineWidth(3)
    pdf.rect(1.5 * cm, 1.5 * cm, width - 3 * cm, height - 3 * cm)

    # Title
    pdf.setFont("Helvetica-Bold", 40)
    pdf.drawCentredString(width / 2, height - 5 * cm, "Certificate of Achievement")

    # Body text
    pdf.setFont("Helvetica", 18)
    pdf.drawCentredString(width / 2, height - 8 * cm, "This is to certify that")

    # Recipient name
    pdf.setFont("Helvetica-Bold", 32)
    pdf.drawCentredString(width / 2, height - 10.5 * cm, name)

    pdf.setFont("Helvetica", 18)
    pdf.drawCentredString(width / 2, height - 12.5 * cm, "has successfully participated in")

    # Event name
    pdf.setFont("Helvetica-Bold", 26)
    pdf.drawCentredString(width / 2, height - 14.5 * cm, event_name)

    # Footer
    pdf.setFont("Helvetica", 14)
    pdf.drawString(3 * cm, 3 * cm, f"Issued by: {issued_by}")
    pdf.drawRightString(width - 3 * cm, 3 * cm, f"Date: {issue_date}")

    pdf.save()
    return str(file_path)
"""
PDF report generation service using ReportLab.
Generates a dental consultation report saved to PDF_STORAGE_PATH/{clinic_id}/{code}.pdf
"""

import io
import os
import qrcode
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    BaseDocTemplate,
    PageTemplate,
    Frame,
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas

# Internal
from app.core.config import settings
from app.core.exceptions import ServerException
from app.constants.messages import REPORT_GENERATION_FAILED


# ── Brand colours ───────────────────────────────────────────────────────────
BRAND       = colors.HexColor("#1a3a5c")
BRAND_LIGHT = colors.HexColor("#e8f0f8")
GREY_LINE   = colors.HexColor("#cccccc")
GREY_TEXT   = colors.HexColor("#555555")
ALT_ROW     = colors.HexColor("#f5f8fc")
PAGE_W, PAGE_H = A4


# ── QR code helper ───────────────────────────────────────────────────────────
def _make_qr_image(data: str, size_px: int = 120) -> ImageReader:
    qr = qrcode.QRCode(box_size=4, border=2,
                       error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a3a5c", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


# ── Vertical rotated-text flowable (report-ID sidebar) ──────────────────────
class VerticalText(Flowable):
    """Draws rotated text; used as an absolute overlay via the canvas callback."""
    def __init__(self, text, font="Helvetica", size=7, color=colors.grey):
        super().__init__()
        self.text  = text
        self.font  = font
        self.size  = size
        self.color = color
        self.width = self.height = 0   # zero-size; drawn via on_page

    def draw(self): pass


# ── Page callback: draws QR + vertical report-id + footer contact bar ────────
BANNER_H = 2.8 * cm   # height of the top header banner


def _make_page_callback(clinic, appointment_code, qr_reader):
    def on_page(canv: rl_canvas.Canvas, doc):
        canv.saveState()
        w, h = PAGE_W, PAGE_H

        # ── Header banner ────────────────────────────────────────────────────
        banner_y = h - BANNER_H
        canv.setFillColor(BRAND)
        canv.rect(0, banner_y, w, BANNER_H, fill=1, stroke=0)

        # Clinic name
        canv.setFillColor(colors.white)
        canv.setFont("Helvetica-Bold", 15)
        canv.drawString(1.8 * cm, banner_y + BANNER_H - 1.05 * cm, clinic.name or "Dental Clinic")
        # small margin bottom, then reg lines (if any) in smaller font, aligned left and stacked with small line spacing
        canv.drawString(1.8 * cm, banner_y + BANNER_H - 1.35 * cm, "")
        # Reg lines
        reg_lines = []
        if getattr(clinic, "gst_number", None):
            reg_lines.append(f"GST: {clinic.gst_number}")
        if getattr(clinic, "reg_number", None):
            reg_lines.append(f"Reg. No: {clinic.reg_number}")
        if getattr(clinic, "reg_office", None):
            reg_lines.append(f"Reg. Office: {clinic.reg_office}")
        if getattr(clinic, "dentist_reg_id", None):
            reg_lines.append(f"Dentist Reg. ID: {clinic.dentist_reg_id}")

        canv.setFont("Helvetica", 6.5)
        canv.setFillColor(colors.HexColor("#b0c8e0"))
        for i, line in enumerate(reg_lines):
            canv.drawString(1.8 * cm, banner_y + BANNER_H - 1.35 * cm - i * 0.38 * cm, line)
        # Dentist name shown separately at bottom of reg lines, in slightly larger font (if present)
        if getattr(clinic, "dentist_name", None):
            dentist_name = f"{clinic.dentist_name}"
            canv.setFillColor(colors.white)
            canv.setFont("Helvetica-Bold", 8)
            canv.drawString(1.8 * cm, banner_y + BANNER_H - 1.35 * cm - len(reg_lines) * 0.38 * cm, dentist_name)

        # QR — vertically centred in banner, flush right
        qr_side = 2.2 * cm
        qr_x = w - 1.8 * cm - qr_side
        qr_y = banner_y + (BANNER_H - qr_side) / 2
        canv.drawImage(qr_reader, qr_x, qr_y,
                       width=qr_side, height=qr_side,
                       preserveAspectRatio=True, mask="auto")
        canv.setFont("Helvetica", 5.5)
        canv.setFillColor(colors.HexColor("#b0c8e0"))
        canv.drawCentredString(qr_x + qr_side / 2, qr_y - 0.25 * cm, "Scan to verify")

        # ── Vertical report-id strip – right edge, bottom half ──────────────
        canv.saveState()
        label = f"Report ID: {appointment_code}"
        canv.setFont("Helvetica", 6.5)
        canv.setFillColor(colors.HexColor("#aaaaaa"))
        # rotate around the right-margin, vertically centred on lower half
        x_strip = w - 0.55 * cm
        y_strip = h * 0.28
        canv.translate(x_strip, y_strip)
        canv.rotate(90)
        canv.drawCentredString(0, 0, label)
        canv.restoreState()

        # ── Footer contact bar (two lines) ──────────────────────────────────
        bar_h = 1.5 * cm
        canv.setFillColor(BRAND)
        canv.rect(0, 0, w, bar_h, fill=1, stroke=0)

        canv.setFillColor(colors.white)

        # Line 1 — phone / email / website
        contact_parts = []
        if clinic.phone:
            contact_parts.append(f"Ph: {clinic.phone}")
        if getattr(clinic, "email", None):
            contact_parts.append(f"Email: {clinic.email}")
        if getattr(clinic, "website", None):
            contact_parts.append(clinic.website)
        contact_line = "   |   ".join(contact_parts) if contact_parts else clinic.name

        canv.setFont("Helvetica-Bold", 7.5)
        canv.drawCentredString(w / 2, bar_h * 0.64, contact_line)

        # Line 2 — address
        if getattr(clinic, "address", None):
            canv.setFont("Helvetica", 6.8)
            canv.setFillColor(colors.HexColor("#b0c8e0"))
            canv.drawCentredString(w / 2, bar_h * 0.28, clinic.address)

        # ── System-generated note just above bar ────────────────────────────
        canv.setFillColor(GREY_TEXT)
        canv.setFont("Helvetica-Oblique", 6.5)
        canv.drawCentredString(
            w / 2, bar_h + 0.18 * cm,
            "This is a computer-generated document. No physical signature required.",
        )

        canv.restoreState()

    return on_page


# ── Main service ─────────────────────────────────────────────────────────────
class PDFService:

    def generate(
        self,
        *,
        consultation,
        patient,
        clinic,
        medications: list,
        appointment_code: str,
    ) -> str:
        try:
            """
            # Dirs & path
            output_dir = Path("./output") / str(clinic.id)
            output_dir.mkdir(parents=True, exist_ok=True)
            file_path = output_dir / f"{appointment_code}.pdf"
            """
            # Ensure directory exists
            output_dir = Path(settings.PDF_STORAGE_PATH) / str(clinic.id)
            output_dir.mkdir(parents=True, exist_ok=True)
            file_path = output_dir / f"{appointment_code}.pdf"
            # QR data – encode appointment code (extend URL if needed)
            qr_data   = appointment_code
            qr_reader = _make_qr_image(qr_data)

            # Margins:  top small, bottom leaves room for footer bar (1.1 cm) + note
            L_MAR = R_MAR = 2 * cm
            T_MAR = BANNER_H + 0.4 * cm   # clear the canvas-drawn banner
            B_MAR = 1.8 * cm   # footer bar is drawn via canvas, not in story

            on_page = _make_page_callback(clinic, appointment_code, qr_reader)

            doc = BaseDocTemplate(
                str(file_path),
                pagesize=A4,
                rightMargin=R_MAR,
                leftMargin=L_MAR,
                topMargin=T_MAR,
                bottomMargin=B_MAR,
            )
            # Content frame: right edge pulled in ~1 cm to leave room for
            # the rotated vertical strip without clipping
            content_w = PAGE_W - L_MAR - R_MAR - 0.8 * cm
            frame = Frame(L_MAR, B_MAR, content_w, PAGE_H - T_MAR - B_MAR,
                          id="main", leftPadding=0, rightPadding=0,
                          topPadding=0, bottomPadding=0)
            doc.addPageTemplates([PageTemplate(id="main", frames=[frame],
                                               onPage=on_page)])

            # ── Styles ────────────────────────────────────────────────────────
            styles = getSampleStyleSheet()
            def S(name, **kw):
                return ParagraphStyle(name, parent=styles["Normal"], **kw)

            clinic_name_style = S("ClinicName", fontSize=15, textColor=BRAND,
                                  fontName="Helvetica-Bold", spaceAfter=1)
            clinic_reg_style  = S("ClinicReg",  fontSize=8,  textColor=GREY_TEXT,
                                  leading=11)
            section_style     = S("Section", fontSize=10, textColor=BRAND,
                                  fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=3)
            body_style        = S("Body",    fontSize=9,  leading=13)
            label_style       = S("Label",   fontSize=8,  textColor=GREY_TEXT, leading=11)
            small_style       = S("Small",   fontSize=7.5,textColor=GREY_TEXT)

            story = []

            # ═══════════════════════════════════════════════════════════════
            # PATIENT DETAILS BOX
            # ═══════════════════════════════════════════════════════════════
            story.append(Paragraph("Patient Details", section_style))

            def cell(text, bold=False):
                fn = "Helvetica-Bold" if bold else "Helvetica"
                return Paragraph(f'<font name="{fn}">{text}</font>', label_style)

            pd_rows = [
                [cell("Patient Name", bold=True), cell(patient.full_name),
                 cell("Patient Code", bold=True), cell(patient.patient_code)],
                [cell("Age",          bold=True), cell(f"{patient.age} yrs"),
                 cell("Gender",       bold=True), cell(patient.gender or "—")],
                [cell("Phone",        bold=True), cell(patient.phone or "—"),
                 cell("Email",        bold=True), cell(patient.email or "—")],
                [cell("Appointment",  bold=True), cell(appointment_code),
                 cell("Date",         bold=True),
                 cell(str(consultation.created_at.date()))],
            ]
            col_w = [2.8*cm, 5.4*cm, 2.8*cm, (content_w - 11*cm)]
            pd_tbl = Table(pd_rows, colWidths=col_w)
            pd_tbl.setStyle(TableStyle([
                ("BACKGROUND",   (0, 0), (-1, -1), BRAND_LIGHT),
                ("BOX",          (0, 0), (-1, -1), 0.8, BRAND),
                ("LINEBELOW",    (0, 0), (-1, -2), 0.4, GREY_LINE),
                ("FONTSIZE",     (0, 0), (-1, -1), 8.5),
                ("TOPPADDING",   (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
                ("LEFTPADDING",  (0, 0), (-1, -1), 6),
            ]))
            story.append(pd_tbl)
            story.append(Spacer(1, 0.3 * cm))

            # ═══════════════════════════════════════════════════════════════
            # CLINICAL SECTIONS  (consistent style)
            # ═══════════════════════════════════════════════════════════════
            def clinical_section(title: str, content: str | None):
                block = [
                    Paragraph(title, section_style),
                    Paragraph(content or "—", body_style),
                    Spacer(1, 0.15 * cm),
                ]
                story.append(KeepTogether(block))

            clinical_section("Symptoms / Chief Complaint", consultation.symptoms)
            clinical_section("Clinical Notes / Examination", consultation.clinical_notes)
            clinical_section("Diagnosis", consultation.diagnosis)

            # ═══════════════════════════════════════════════════════════════
            # PRESCRIPTION
            # ═══════════════════════════════════════════════════════════════
            story.append(Paragraph("Prescription / Medications", section_style))
            if medications:
                med_data = [["#", "Medicine", "Dosage", "Frequency", "Duration", "Instructions"]]
                for i, m in enumerate(sorted(medications, key=lambda x: x.sort_order), 1):
                    med_data.append([
                        str(i), m.name, m.dosage or "—",
                        m.frequency or "—", m.duration or "—",
                        m.instructions or "—",
                    ])
                cw = [0.6*cm, 4.2*cm, 2.1*cm, 2.8*cm, 2.1*cm, None]
                # Let last col fill remaining
                used = sum(c for c in cw[:-1])
                cw[-1] = content_w - used
                med_tbl = Table(med_data, colWidths=cw)
                med_tbl.setStyle(TableStyle([
                    ("BACKGROUND",   (0, 0), (-1, 0), BRAND),
                    ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
                    ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE",     (0, 0), (-1, -1), 8),
                    ("GRID",         (0, 0), (-1, -1), 0.4, GREY_LINE),
                    ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, ALT_ROW]),
                    ("TOPPADDING",   (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
                    ("LEFTPADDING",  (0, 0), (-1, -1), 4),
                ]))
                story.append(med_tbl)
            else:
                story.append(Paragraph("No medications prescribed.", body_style))

            # ═══════════════════════════════════════════════════════════════
            # FEE + FOLLOW-UP  (subtle, no bold "Consultation Fee" header)
            # ═══════════════════════════════════════════════════════════════
            story.append(Spacer(1, 0.35 * cm))
            misc_rows = []
            # Fee shown only if it is needed for billing context
            # (retained but moved to bottom info area; comment out if unwanted)
            # if consultation.fee_charged is not None:
            #     misc_rows.append(f"Consultation Fee: Rs. {consultation.fee_charged:.2f}")
            if consultation.is_follow_up_required:
                fu = "Follow-up required"
                if consultation.follow_up_days:
                    fu += f" in {consultation.follow_up_days} days"
                if consultation.follow_up_notes:
                    fu += f". Note: {consultation.follow_up_notes}"
                misc_rows.append(fu)
            for row in misc_rows:
                story.append(Paragraph(f"<b>{row}</b>", body_style))

            # ═══════════════════════════════════════════════════════════════
            # SIGNATURE LINE
            # ═══════════════════════════════════════════════════════════════
            story.append(Spacer(1, 0.5 * cm))
            story.append(HRFlowable(width="100%", thickness=0.5,
                                    color=GREY_LINE, spaceAfter=4))
            submitted = (
                consultation.submitted_at.strftime("%d %b %Y  %H:%M")
                if consultation.submitted_at else ""
            )
            story.append(Paragraph(
                f"Signed by: <b>{clinic.dentist_name}</b>  |  Generated: {submitted}",
                label_style,
            ))

            doc.build(story)
            return str(file_path)

        except Exception as exc:
            raise Exception(f"PDF generation failed: {exc}") from exc
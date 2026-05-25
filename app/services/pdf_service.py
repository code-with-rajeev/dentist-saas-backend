"""
PDF report generation service using ReportLab.
Generates a dental consultation report saved to PDF_STORAGE_PATH/{clinic_id}/{code}.pdf
"""

# Standard library
import os
import uuid
from pathlib import Path

# Third-party — ReportLab
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
)

# Internal
from app.core.config import settings
from app.core.exceptions import ServerException
from app.constants.messages import REPORT_GENERATION_FAILED


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
        """
        Build a ReportLab PDF report for the consultation.
        Saves to {PDF_STORAGE_PATH}/{clinic_id}/{appointment_code}.pdf
        Returns the saved file path string.
        Raises ServerException(REPORT_GENERATION_FAILED) on any error.
        """
        try:
            # Ensure directory exists
            output_dir = Path(settings.PDF_STORAGE_PATH) / str(clinic.id)
            output_dir.mkdir(parents=True, exist_ok=True)
            file_path = output_dir / f"{appointment_code}.pdf"

            doc = SimpleDocTemplate(
                str(file_path),
                pagesize=A4,
                rightMargin=2 * cm,
                leftMargin=2 * cm,
                topMargin=2.5 * cm,
                bottomMargin=2 * cm,
            )

            styles = getSampleStyleSheet()
            story = []

            # ---- Header ----
            header_style = ParagraphStyle(
                "ClinicHeader",
                parent=styles["Heading1"],
                fontSize=16,
                textColor=colors.HexColor("#1a3a5c"),
                spaceAfter=4,
            )
            sub_style = ParagraphStyle(
                "ClinicSub",
                parent=styles["Normal"],
                fontSize=9,
                textColor=colors.grey,
            )
            body_style = ParagraphStyle(
                "Body",
                parent=styles["Normal"],
                fontSize=10,
                leading=14,
            )
            label_style = ParagraphStyle(
                "Label",
                parent=styles["Normal"],
                fontSize=9,
                textColor=colors.HexColor("#555555"),
                leading=12,
            )
            section_style = ParagraphStyle(
                "Section",
                parent=styles["Heading2"],
                fontSize=11,
                textColor=colors.HexColor("#1a3a5c"),
                spaceBefore=12,
                spaceAfter=4,
            )

            story.append(Paragraph(clinic.name or "Dental Clinic", header_style))
            story.append(Paragraph(clinic.address or "", sub_style))
            if clinic.phone:
                story.append(Paragraph(f"Phone: {clinic.phone}", sub_style))
            story.append(Paragraph(
                f"Reg. No: {clinic.dentist_reg_id}   |   {clinic.dentist_name}",
                sub_style,
            ))
            story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1a3a5c"), spaceAfter=8))

            # ---- Patient Info ----
            story.append(Paragraph("Consultation Report", section_style))

            patient_data = [
                ["Patient Name:", patient.full_name, "Patient Code:", patient.patient_code],
                ["Age:", f"{patient.age} years", "Gender:", patient.gender or "—"],
                ["Phone:", patient.phone or "—", "Email:", patient.email or "—"],
                ["Appointment:", appointment_code, "Date:", str(consultation.created_at.date())],
            ]
            pt = Table(patient_data, colWidths=[3.5 * cm, 6.5 * cm, 3.5 * cm, 4.5 * cm])
            pt.setStyle(TableStyle([
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#555555")),
                ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#555555")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(pt)
            story.append(Spacer(1, 0.4 * cm))

            # ---- Clinical Details ----
            def _section(title: str, content: str | None, style):
                story.append(Paragraph(title, section_style))
                story.append(Paragraph(content or "—", style))

            _section("Symptoms / Chief Complaint", consultation.symptoms, body_style)
            _section("Clinical Notes / Examination", consultation.clinical_notes, body_style)
            _section("Diagnosis", consultation.diagnosis, body_style)

            # ---- Medications ----
            story.append(Paragraph("Prescription / Medications", section_style))
            if medications:
                med_data = [["#", "Medicine", "Dosage", "Frequency", "Duration", "Instructions"]]
                for i, m in enumerate(sorted(medications, key=lambda x: x.sort_order), 1):
                    med_data.append([
                        str(i),
                        m.name,
                        m.dosage or "—",
                        m.frequency or "—",
                        m.duration or "—",
                        m.instructions or "—",
                    ])
                med_table = Table(
                    med_data,
                    colWidths=[0.7 * cm, 4.5 * cm, 2.3 * cm, 3 * cm, 2.3 * cm, 5.2 * cm],
                )
                med_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f8fc")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(med_table)
            else:
                story.append(Paragraph("No medications prescribed.", body_style))

            # ---- Fee + Follow-up ----
            story.append(Spacer(1, 0.4 * cm))
            if consultation.fee_charged is not None:
                story.append(Paragraph(
                    f"<b>Consultation Fee:</b> Rs. {consultation.fee_charged:.2f}", body_style
                ))
            if consultation.is_follow_up_required:
                fu_text = f"Follow-up required"
                if consultation.follow_up_days:
                    fu_text += f" in {consultation.follow_up_days} days"
                if consultation.follow_up_notes:
                    fu_text += f". Note: {consultation.follow_up_notes}"
                story.append(Paragraph(f"<b>{fu_text}</b>", body_style))

            # ---- Footer ----
            story.append(Spacer(1, 0.8 * cm))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceAfter=4))
            story.append(Paragraph(
                f"Signed by: Dr. {clinic.dentist_name}  |  Report generated: {consultation.submitted_at.strftime('%d %b %Y %H:%M') if consultation.submitted_at else ''}",
                label_style,
            ))
            story.append(Paragraph(
                "This is a computer-generated document. No physical signature required.",
                label_style,
            ))

            doc.build(story)
            return str(file_path)

        except Exception as exc:
            raise ServerException(
                code=REPORT_GENERATION_FAILED,
                message=f"PDF generation failed: {exc}",
            ) from exc

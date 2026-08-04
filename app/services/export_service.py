import csv
import io
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def export_csv(headers, rows):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    mem.seek(0)
    return mem


def export_excel(headers, rows, sheet_title="Report"):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title[:31]
    ws.append(headers)
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = cell.font.copy(bold=True)
    for row in rows:
        ws.append(list(row))
    for col_cells in ws.columns:
        length = max(len(str(c.value)) if c.value is not None else 0 for c in col_cells)
        ws.column_dimensions[col_cells[0].column_letter].width = min(max(length + 2, 10), 40)
    mem = io.BytesIO()
    wb.save(mem)
    mem.seek(0)
    return mem


def export_pdf_table(title, headers, rows, subtitle=None):
    mem = io.BytesIO()
    doc = SimpleDocTemplate(mem, pagesize=A4, topMargin=20 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleStyle", parent=styles["Heading1"], fontSize=16, spaceAfter=4)
    subtitle_style = ParagraphStyle("SubtitleStyle", parent=styles["Normal"], fontSize=10, textColor=colors.grey)

    elements = [Paragraph(title, title_style)]
    if subtitle:
        elements.append(Paragraph(subtitle, subtitle_style))
    elements.append(Spacer(1, 10))

    table_data = [headers] + [[str(c) for c in row] for row in rows]
    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b4332")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f0")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    mem.seek(0)
    return mem


def generate_application_pdf(school, application):
    mem = io.BytesIO()
    doc = SimpleDocTemplate(mem, pagesize=letter, topMargin=15 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=16, alignment=1)
    section_style = ParagraphStyle("Section", parent=styles["Heading3"], fontSize=11, spaceBefore=14, spaceAfter=6,
                                    textColor=colors.HexColor("#1b4332"))
    normal = styles["Normal"]

    elements = [
        Paragraph(school.name if school else "Madrassa", title_style),
        Paragraph("Student Admission Application Form", ParagraphStyle("sub", parent=normal, alignment=1, spaceAfter=6)),
    ]
    if school and school.address:
        elements.append(Paragraph(school.address, ParagraphStyle("addr", parent=normal, alignment=1, fontSize=9, textColor=colors.grey)))
    elements.append(Spacer(1, 14))

    def kv_table(rows):
        t = Table(rows, colWidths=[130, 350])
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ]))
        return t

    elements.append(Paragraph("Student Information", section_style))
    elements.append(kv_table([
        ["Full Name:", application.full_name],
        ["Gender:", (application.gender or "-").title()],
        ["Date of Birth:", application.date_of_birth.strftime("%d %b %Y") if application.date_of_birth else "-"],
        ["Previous School:", application.previous_school or "-"],
        ["Address:", application.address or "-"],
    ]))

    elements.append(Paragraph("Parent / Guardian Information", section_style))
    elements.append(kv_table([
        ["Name:", application.guardian_name],
        ["Phone:", application.guardian_phone],
        ["Occupation:", application.guardian_occupation or "-"],
        ["Address:", application.guardian_address or "-"],
    ]))

    elements.append(Paragraph("Emergency Contact", section_style))
    elements.append(kv_table([
        ["Name:", application.emergency_contact_name or "-"],
        ["Phone:", application.emergency_contact_phone or "-"],
        ["Relationship:", application.emergency_contact_relationship or "-"],
    ]))

    elements.append(Spacer(1, 24))
    elements.append(Paragraph(f"Application Date: {application.application_date}", normal))
    elements.append(Paragraph(f"Status: {application.status_label}", normal))
    elements.append(Spacer(1, 36))
    elements.append(Paragraph("_____________________________", normal))
    elements.append(Paragraph("Parent / Guardian Signature", ParagraphStyle("sig", parent=normal, fontSize=9, textColor=colors.grey)))

    doc.build(elements)
    mem.seek(0)
    return mem


def generate_receipt_pdf(school, student, payment, collector):
    mem = io.BytesIO()
    doc = SimpleDocTemplate(mem, pagesize=letter, topMargin=15 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=18, alignment=1)
    normal = styles["Normal"]

    elements = [
        Paragraph(school.name if school else "Madrassa", title_style),
        Paragraph("Official Payment Receipt", ParagraphStyle("sub", parent=normal, alignment=1, spaceAfter=14)),
        Spacer(1, 10),
    ]

    data = [
        ["Receipt No:", payment.receipt_number, "Date:", payment.payment_date.strftime("%d %b %Y")],
        ["Student:", student.full_name, "Student ID:", student.student_id],
        ["Payment Type:", payment.payment_type_label, "Amount:", f"{payment.amount:.2f}"],
        ["Collected By:", collector.full_name if collector else "-", "Remarks:", payment.remarks or "-"],
    ]
    table = Table(data, colWidths=[90, 150, 90, 150])
    table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Thank you for your payment.", normal))
    doc.build(elements)
    mem.seek(0)
    return mem

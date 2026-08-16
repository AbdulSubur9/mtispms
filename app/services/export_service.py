import csv
import io
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.services.document_branding import branded_header, branded_footer, signature_block, bilingual_label

_styles = getSampleStyleSheet()


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


def export_pdf_table(title, headers, rows, subtitle=None, school=None):
    """Generic tabular PDF export (reports, exports). Includes the school's
    branding (logo/name/contact) when a school is supplied."""
    mem = io.BytesIO()
    doc = SimpleDocTemplate(mem, pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm)

    elements = branded_header(school, title, subtitle=subtitle) if school else _plain_title(title, subtitle)

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
    if school:
        elements.extend(branded_footer(school))
    doc.build(elements)
    mem.seek(0)
    return mem


def _plain_title(title, subtitle=None):
    """Fallback header used when no school/branding is available."""
    title_style = ParagraphStyle("TitleStyle", parent=_styles["Heading1"], fontSize=16, spaceAfter=4)
    subtitle_style = ParagraphStyle("SubtitleStyle", parent=_styles["Normal"], fontSize=10, textColor=colors.grey)
    elements = [Paragraph(title, title_style)]
    if subtitle:
        elements.append(Paragraph(subtitle, subtitle_style))
    elements.append(Spacer(1, 10))
    return elements


def _kv_table(rows, col_widths=(150, 330)):
    t = Table(rows, colWidths=list(col_widths))
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#e0e0e0")),
    ]))
    return t


def _section_heading(text):
    style = ParagraphStyle(
        "SectionHeading", parent=_styles["Heading3"], fontSize=11.5, spaceBefore=14, spaceAfter=6,
        textColor=colors.white, backColor=colors.HexColor("#2d6a4f"),
        leftIndent=6, borderPadding=(4, 4, 4, 4),
    )
    return Paragraph(text, style)


def generate_application_pdf(school, application):
    """Professional, branded student admission/application form. Mirrors
    the reference form's structure (bilingual section headings, student
    info, parent/guardian info, health declaration, emergency contact,
    signatures, school contact footer) while using this app's own
    reusable document-branding architecture rather than a screenshot of
    the original."""
    mem = io.BytesIO()
    doc = SimpleDocTemplate(mem, pagesize=A4, topMargin=14 * mm, bottomMargin=14 * mm,
                             leftMargin=18 * mm, rightMargin=18 * mm)

    elements = branded_header(
        school, bilingual_label("Student Admission Application Form", "استمارة طلب القبول"),
        subtitle=f"Admission No: {application.student.student_id if application.student else 'Pending Approval'}"
                 f"   |   Application Date: {application.application_date}",
    )

    # ---- Student photograph placeholder + core details side by side ----
    photo_placeholder = Table([[Paragraph(
        bilingual_label("Photo", "صورة"),
        ParagraphStyle("photoLabel", parent=_styles["Normal"], alignment=1, fontSize=8, textColor=colors.grey),
    )]], colWidths=[90], rowHeights=[110])
    photo_placeholder.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#999999")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))

    student_info = _kv_table([
        [bilingual_label("Full Name", "الاسم الكامل") + ":", application.full_name],
        [bilingual_label("Gender", "الجنس") + ":", (application.gender or "-").title()],
        [bilingual_label("Date of Birth", "تاريخ الميلاد") + ":",
         application.date_of_birth.strftime("%d %b %Y") if application.date_of_birth else "-"],
        [bilingual_label("Previous School", "المدرسة السابقة") + ":", application.previous_school or "-"],
        [bilingual_label("Address", "العنوان") + ":", application.address or "-"],
    ], col_widths=(120, 260))

    layout = Table([[photo_placeholder, student_info]], colWidths=[100, 390])
    layout.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(_section_heading(bilingual_label("Student Information", "معلومات الطالب")))
    elements.append(layout)

    elements.append(_section_heading(bilingual_label("Parent / Guardian Information", "معلومات ولي الأمر")))
    elements.append(_kv_table([
        [bilingual_label("Name", "الاسم") + ":", application.guardian_name],
        [bilingual_label("Phone", "الهاتف") + ":", application.guardian_phone],
        [bilingual_label("Occupation", "المهنة") + ":", application.guardian_occupation or "-"],
        [bilingual_label("Address", "العنوان") + ":", application.guardian_address or "-"],
    ]))

    elements.append(_section_heading(bilingual_label("Health Information", "المعلومات الصحية")))
    elements.append(_kv_table([
        [bilingual_label("Medical Condition", "حالة طبية") + ":", "Yes" if application.has_medical_condition else "No"],
        [bilingual_label("Details", "التفاصيل") + ":", application.medical_condition_details or "-"],
    ]))

    elements.append(_section_heading(bilingual_label("Emergency Contact", "جهة اتصال الطوارئ")))
    elements.append(_kv_table([
        [bilingual_label("Name", "الاسم") + ":", application.emergency_contact_name or "-"],
        [bilingual_label("Phone", "الهاتف") + ":", application.emergency_contact_phone or "-"],
        [bilingual_label("Relationship", "صلة القرابة") + ":", application.emergency_contact_relationship or "-"],
    ]))

    elements.append(Spacer(1, 10))
    declaration_style = ParagraphStyle("Declaration", parent=_styles["Normal"], fontSize=9, textColor=colors.HexColor("#333333"))
    elements.append(Paragraph(
        bilingual_label(
            "Declaration: I declare that the information provided in this application is true and "
            "accurate to the best of my knowledge, and I agree to abide by the rules and regulations "
            "of the Madrasah.",
            "إقرار: أقر بأن المعلومات المقدمة في هذا الطلب صحيحة ودقيقة حسب علمي، وأوافق على الالتزام "
            "بقواعد ولوائح المدرسة.",
        ),
        declaration_style,
    ))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        f"Declaration accepted: {'Yes' if application.declaration_accepted else 'No'}   |   "
        f"Status: {application.status_label}",
        declaration_style,
    ))

    elements.append(Spacer(1, 30))
    elements.append(signature_block([
        bilingual_label("Parent/Guardian Signature", "توقيع ولي الأمر"),
        bilingual_label("Administrator Signature", "توقيع الإدارة"),
    ]))

    elements.extend(branded_footer(school))
    doc.build(elements)
    mem.seek(0)
    return mem


def generate_receipt_pdf(school, student, payment, collector):
    mem = io.BytesIO()
    doc = SimpleDocTemplate(mem, pagesize=letter, topMargin=14 * mm, bottomMargin=14 * mm)

    elements = branded_header(school, "Official Payment Receipt")

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
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Thank you for your payment.", _styles["Normal"]))
    elements.extend(branded_footer(school))
    doc.build(elements)
    mem.seek(0)
    return mem


def generate_student_report_pdf(school, exam, result_row, ordinal_fn):
    """Individual student academic report (section 16): school branding,
    student photo/details, per-subject marks, total/average/percentage,
    grade, class position, teacher comments, signatures."""
    mem = io.BytesIO()
    doc = SimpleDocTemplate(mem, pagesize=A4, topMargin=14 * mm, bottomMargin=14 * mm,
                             leftMargin=18 * mm, rightMargin=18 * mm)

    student = result_row["student"]
    elements = branded_header(
        school, "Individual Academic Report",
        subtitle=f"{exam.name}   |   Class: {exam.classroom.name}   |   Date: {exam.start_date or '-'}",
    )

    photo_cell = None
    if student.photo:
        try:
            from flask import current_app
            import os as _os
            photo_path = _os.path.join(current_app.static_folder, student.photo)
            if _os.path.isfile(photo_path):
                photo_cell = Image(photo_path, width=70, height=70)
        except Exception:
            photo_cell = None
    if photo_cell is None:
        photo_cell = Paragraph("Photo", ParagraphStyle("ph", parent=_styles["Normal"], alignment=1, fontSize=8, textColor=colors.grey))

    info_table = _kv_table([
        ["Student Name:", student.full_name],
        ["Student ID:", student.student_id],
        ["Class:", exam.classroom.name],
    ], col_widths=(100, 280))

    layout = Table([[photo_cell, info_table]], colWidths=[90, 400])
    layout.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (0, 0), "CENTER")]))
    elements.append(layout)
    elements.append(Spacer(1, 12))

    if result_row["subject_results"]:
        rows = [["Subject", "Max Marks", "Marks Obtained", "Comment"]]
        for exam_subject_id, res in result_row["subject_results"].items():
            rows.append([
                res.exam_subject.subject.name, f"{res.exam_subject.max_marks:.0f}",
                f"{res.marks_obtained:.2f}", res.teacher_comment or "-",
            ])
        table = Table(rows, colWidths=[160, 80, 100, 150])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b4332")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 14))

        summary_table = _kv_table([
            ["Total Marks:", f"{result_row['total']:.2f} / {result_row['max_total']:.0f}"],
            ["Average:", f"{result_row['average']:.2f}"],
            ["Percentage:", f"{result_row['percentage']:.1f}%"],
            ["Grade:", f"{result_row['grade']} ({result_row['remark']})"],
            ["Class Position:", ordinal_fn(result_row["position"])],
        ], col_widths=(140, 240))
        elements.append(summary_table)
    else:
        elements.append(Paragraph("No results have been recorded for this student yet.", _styles["Normal"]))

    elements.append(Spacer(1, 30))
    elements.append(signature_block(["Teacher Signature", "Administrator Signature"]))
    elements.extend(branded_footer(school))
    doc.build(elements)
    mem.seek(0)
    return mem


def generate_class_result_sheet_pdf(school, exam, summary, ordinal_fn):
    """Whole-class result sheet (section 17): one row per student, one
    column per subject, plus total/average/grade/position, on a single
    landscape-friendly A4 layout with school branding."""
    from reportlab.lib.pagesizes import landscape

    mem = io.BytesIO()
    doc = SimpleDocTemplate(mem, pagesize=landscape(A4), topMargin=12 * mm, bottomMargin=12 * mm,
                             leftMargin=12 * mm, rightMargin=12 * mm)

    elements = branded_header(
        school, "Class Result Sheet",
        subtitle=f"{exam.name}   |   Class: {exam.classroom.name}   |   Date: {exam.start_date or '-'}",
    )

    exam_subjects = exam.exam_subjects.all()
    headers = ["#", "Student", "Student ID"] + [es.subject.name for es in exam_subjects] + [
        "Total", "Average", "%", "Grade", "Position"
    ]
    rows = [headers]
    for i, row in enumerate(summary, start=1):
        subject_cells = []
        for es in exam_subjects:
            res = row["subject_results"].get(es.id)
            subject_cells.append(f"{res.marks_obtained:.1f}" if res else "-")
        rows.append([
            str(i), row["student"].full_name, row["student"].student_id,
            *subject_cells,
            f"{row['total']:.1f}" if row["total"] is not None else "-",
            f"{row['average']:.1f}" if row["average"] is not None else "-",
            f"{row['percentage']:.1f}" if row["percentage"] is not None else "-",
            row["grade"] or "-",
            ordinal_fn(row["position"]),
        ])

    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b4332")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f0")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(table)
    elements.extend(branded_footer(school))
    doc.build(elements)
    mem.seek(0)
    return mem


# ---------------------------------------------------------------------------
# Student ID Card
# ---------------------------------------------------------------------------

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode.code128 import Code128


def generate_student_id_card_pdf(student, school):
    """Generate a credit-card sized student ID card (54mm x 86mm)."""
    width, height = 86 * mm, 54 * mm
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))

    # Background
    c.setFillColorRGB(0.97, 0.97, 0.97)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # School header bar
    c.setFillColorRGB(0.1, 0.3, 0.6)
    c.rect(0, height - 12 * mm, width, 12 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(width / 2, height - 8 * mm, school.name[:35])

    # Photo area
    photo_y = height - 38 * mm
    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    c.rect(3 * mm, photo_y, 20 * mm, 25 * mm, fill=0, stroke=1)

    # Student details
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(26 * mm, height - 18 * mm, student.full_name[:28])
    c.setFont("Helvetica", 7)
    c.drawString(26 * mm, height - 23 * mm, f"ID: {student.student_id}")
    c.drawString(26 * mm, height - 27 * mm, f"Class: {student.classroom.name if student.classroom else 'N/A'}")
    c.drawString(26 * mm, height - 31 * mm, f"DOB: {student.date_of_birth.strftime('%d/%m/%Y') if student.date_of_birth else 'N/A'}")

    # Barcode
    barcode = Code128(student.student_id, barWidth=0.3 * mm, barHeight=6 * mm)
    barcode.drawOn(c, 26 * mm, 4 * mm)

    c.save()
    buf.seek(0)
    return buf

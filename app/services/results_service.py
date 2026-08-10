"""
Result aggregation and ranking for an exam.

Ranking uses "competition ranking" (1224 style, sometimes called "standard
competition ranking"): tied students share the same rank, and the rank
after a tie skips ahead by the number of tied students. That matches the
spec exactly - two students tied for best get 1st and 1st, and the next
student is 3rd (not 2nd), because two people are already "ahead" of them.
"""
from collections import defaultdict
from app.extensions import db
from app.models import ExamSubject, Result, Student, GradingScaleBand


def compute_exam_summary(exam):
    """Returns a list of dicts, one per student in the exam's class, each
    with: student, subject_results (dict of subject_id -> Result), total,
    max_total, average, percentage, grade, remark, position. Students with
    zero recorded results for this exam are excluded from ranking (they
    haven't been assessed yet) but still listed."""
    exam_subjects = exam.exam_subjects.all()
    if not exam_subjects:
        return []

    exam_subject_ids = [es.id for es in exam_subjects]
    max_total = sum(float(es.max_marks) for es in exam_subjects)

    results = Result.query.filter(Result.exam_subject_id.in_(exam_subject_ids)).all()
    by_student = defaultdict(dict)
    for r in results:
        by_student[r.student_id][r.exam_subject_id] = r

    students = exam.classroom.students.filter_by(status="active").order_by(Student.first_name).all()

    rows = []
    for student in students:
        subject_results = by_student.get(student.id, {})
        if not subject_results:
            rows.append({
                "student": student, "subject_results": {}, "total": None, "max_total": max_total,
                "average": None, "percentage": None, "grade": None, "remark": None, "position": None,
            })
            continue

        total = sum(float(r.marks_obtained) for r in subject_results.values())
        percentage = (total / max_total * 100) if max_total else 0
        average = total / len(subject_results) if subject_results else 0
        grade, remark = GradingScaleBand.grade_for_percentage(exam.school_id, percentage)

        rows.append({
            "student": student, "subject_results": subject_results, "total": total, "max_total": max_total,
            "average": average, "percentage": percentage, "grade": grade, "remark": remark, "position": None,
        })

    _assign_competition_ranks(rows)
    return rows


def _assign_competition_ranks(rows):
    """Mutates `rows` in place, setting `position` using standard
    competition ranking (ties share a rank; the next rank skips ahead).
    Rows with no results (percentage is None) are left unranked."""
    ranked = [r for r in rows if r["percentage"] is not None]
    ranked.sort(key=lambda r: r["percentage"], reverse=True)

    position = 0
    seen = 0
    last_percentage = None
    for row in ranked:
        seen += 1
        if row["percentage"] != last_percentage:
            position = seen
            last_percentage = row["percentage"]
        row["position"] = position


def ordinal(n):
    if n is None:
        return "-"
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"

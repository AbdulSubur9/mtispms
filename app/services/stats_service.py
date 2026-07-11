from datetime import date, timedelta
from sqlalchemy import func
from app.extensions import db
from app.models import Payment, Expense, Student


def _base_payment_query(school_id):
    q = Payment.query.filter(Payment.is_void.is_(False))
    if school_id is not None:
        q = q.filter(Payment.school_id == school_id)
    return q


def _base_expense_query(school_id):
    q = Expense.query
    if school_id is not None:
        q = q.filter(Expense.school_id == school_id)
    return q


def total_students(school_id):
    q = Student.query.filter(Student.status == "active")
    if school_id is not None:
        q = q.filter(Student.school_id == school_id)
    return q.count()


def collections_between(school_id, start_date, end_date):
    q = _base_payment_query(school_id).filter(
        Payment.payment_date >= start_date, Payment.payment_date <= end_date
    )
    total = q.with_entities(func.coalesce(func.sum(Payment.amount), 0)).scalar()
    return float(total or 0)


def expenses_between(school_id, start_date, end_date):
    q = _base_expense_query(school_id).filter(
        Expense.expense_date >= start_date, Expense.expense_date <= end_date
    )
    total = q.with_entities(func.coalesce(func.sum(Expense.amount), 0)).scalar()
    return float(total or 0)


def total_income(school_id):
    total = _base_payment_query(school_id).with_entities(func.coalesce(func.sum(Payment.amount), 0)).scalar()
    return float(total or 0)


def total_expenses(school_id):
    total = _base_expense_query(school_id).with_entities(func.coalesce(func.sum(Expense.amount), 0)).scalar()
    return float(total or 0)


def current_balance(school_id):
    return total_income(school_id) - total_expenses(school_id)


def payment_trend(school_id, days=30):
    """Returns list of (date, total) for the last `days` days."""
    end = date.today()
    start = end - timedelta(days=days - 1)
    rows = (
        _base_payment_query(school_id)
        .filter(Payment.payment_date >= start, Payment.payment_date <= end)
        .with_entities(Payment.payment_date, func.sum(Payment.amount))
        .group_by(Payment.payment_date)
        .order_by(Payment.payment_date)
        .all()
    )
    by_date = {r[0]: float(r[1]) for r in rows}
    result = []
    d = start
    while d <= end:
        result.append((d, by_date.get(d, 0.0)))
        d += timedelta(days=1)
    return result


def expense_trend(school_id, days=30):
    end = date.today()
    start = end - timedelta(days=days - 1)
    rows = (
        _base_expense_query(school_id)
        .filter(Expense.expense_date >= start, Expense.expense_date <= end)
        .with_entities(Expense.expense_date, func.sum(Expense.amount))
        .group_by(Expense.expense_date)
        .order_by(Expense.expense_date)
        .all()
    )
    by_date = {r[0]: float(r[1]) for r in rows}
    result = []
    d = start
    while d <= end:
        result.append((d, by_date.get(d, 0.0)))
        d += timedelta(days=1)
    return result


def expense_category_breakdown(school_id):
    rows = (
        _base_expense_query(school_id)
        .with_entities(Expense.category, func.sum(Expense.amount))
        .group_by(Expense.category)
        .all()
    )
    return [(r[0], float(r[1])) for r in rows]


def students_paid_vs_owing(school_id, period_start=None, period_end=None):
    """Very simple heuristic: a student counts as 'paid' if they have at least one
    non-void payment in the given period (defaults to current month)."""
    if period_start is None:
        today = date.today()
        period_start = today.replace(day=1)
    if period_end is None:
        period_end = date.today()

    paid_student_ids = {
        r[0]
        for r in _base_payment_query(school_id)
        .filter(Payment.payment_date >= period_start, Payment.payment_date <= period_end)
        .with_entities(Payment.student_id)
        .distinct()
        .all()
    }
    students_q = Student.query.filter(Student.status == "active")
    if school_id is not None:
        students_q = students_q.filter(Student.school_id == school_id)
    total = students_q.count()
    paid = students_q.filter(Student.id.in_(paid_student_ids)).count() if paid_student_ids else 0
    owing = total - paid
    return paid, owing


def collector_performance(school_id, start_date=None, end_date=None):
    q = _base_payment_query(school_id)
    if start_date:
        q = q.filter(Payment.payment_date >= start_date)
    if end_date:
        q = q.filter(Payment.payment_date <= end_date)
    rows = (
        q.with_entities(Payment.collector_id, func.count(Payment.id), func.sum(Payment.amount))
        .group_by(Payment.collector_id)
        .order_by(func.sum(Payment.amount).desc())
        .all()
    )
    return rows

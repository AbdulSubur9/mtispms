from datetime import date
from app.extensions import db
from app.models import Student, Payment, Expense, ClassRoom
from app.models.payment import PaymentType
from app.models.expense import ExpenseCategory


def test_student_id_generation(app, school):
    sid1 = Student.generate_student_id(school.id)
    assert sid1 == "STU-0001"

    s = Student(school_id=school.id, student_id=sid1, first_name="Ali", last_name="Bello",
                gender="male", guardian_name="Guardian", guardian_contact="0800000000")
    db.session.add(s)
    db.session.commit()

    sid2 = Student.generate_student_id(school.id)
    assert sid2 == "STU-0002"


def test_receipt_number_generation(app, school):
    rn = Payment.generate_receipt_number(school.id)
    assert rn.startswith("RCT-")


def test_expense_reference_generation(app, school):
    ref = Expense.generate_reference_number(school.id)
    assert ref.startswith("EXP-")


def test_school_balance_calculation(app, school, super_admin):
    student = Student(school_id=school.id, student_id="STU-0001", first_name="Ali", last_name="Bello",
                       gender="male", guardian_name="Guardian", guardian_contact="0800000000")
    db.session.add(student)
    db.session.flush()

    payment = Payment(school_id=school.id, student_id=student.id, collector_id=super_admin.id,
                       receipt_number="RCT-26-00001", amount=1000, payment_type=PaymentType.WEEKLY,
                       payment_date=date.today())
    db.session.add(payment)

    expense = Expense(school_id=school.id, reference_number="EXP-26-00001", amount=400,
                       purpose="Test expense", category=ExpenseCategory.OTHERS, recorded_by_id=super_admin.id,
                       expense_date=date.today())
    db.session.add(expense)
    db.session.commit()

    assert school.total_income == 1000.0
    assert school.total_expenses == 400.0
    assert school.current_balance == 600.0


def test_voided_payment_excluded_from_income(app, school, super_admin):
    student = Student(school_id=school.id, student_id="STU-0001", first_name="Ali", last_name="Bello",
                       gender="male", guardian_name="Guardian", guardian_contact="0800000000")
    db.session.add(student)
    db.session.flush()

    payment = Payment(school_id=school.id, student_id=student.id, collector_id=super_admin.id,
                       receipt_number="RCT-26-00001", amount=1000, payment_type=PaymentType.WEEKLY,
                       payment_date=date.today(), is_void=True)
    db.session.add(payment)
    db.session.commit()

    assert school.total_income == 0.0


def test_classroom_student_count(app, school):
    classroom = ClassRoom(school_id=school.id, name="Class A")
    db.session.add(classroom)
    db.session.flush()

    s1 = Student(school_id=school.id, student_id="STU-0001", first_name="A", last_name="B", gender="male",
                 guardian_name="G", guardian_contact="0800000000", class_id=classroom.id, status="active")
    s2 = Student(school_id=school.id, student_id="STU-0002", first_name="C", last_name="D", gender="female",
                 guardian_name="G", guardian_contact="0800000000", class_id=classroom.id, status="inactive")
    db.session.add_all([s1, s2])
    db.session.commit()

    assert classroom.student_count == 1

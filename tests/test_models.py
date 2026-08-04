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


# ---------------------------------------------------------------------------
# Regression tests for the multi-tenant ID-collision bug: two DIFFERENT
# schools must each be able to independently create a "#0001" student,
# receipt, and expense reference without an IntegrityError. Before the
# composite-unique-constraint fix, the second school's first insert of each
# type would fail because student_id/receipt_number/reference_number were
# (incorrectly) globally unique columns.
# ---------------------------------------------------------------------------

def test_two_schools_can_each_have_student_0001(app, school):
    from app.models import School

    second_school = School(name="Second School", code="SEC002")
    db.session.add(second_school)
    db.session.flush()

    s1 = Student(school_id=school.id, student_id=Student.generate_student_id(school.id),
                 first_name="A", last_name="One", gender="male", guardian_name="G", guardian_contact="0800000001")
    s2 = Student(school_id=second_school.id, student_id=Student.generate_student_id(second_school.id),
                 first_name="B", last_name="Two", gender="male", guardian_name="G", guardian_contact="0800000002")
    db.session.add_all([s1, s2])
    db.session.commit()  # must NOT raise IntegrityError

    assert s1.student_id == "STU-0001"
    assert s2.student_id == "STU-0001"
    assert s1.school_id != s2.school_id


def test_two_schools_can_each_have_receipt_00001(app, school, super_admin):
    from app.models import School

    second_school = School(name="Second School", code="SEC003")
    db.session.add(second_school)
    db.session.flush()

    student_a = Student(school_id=school.id, student_id="STU-0001", first_name="A", last_name="One",
                         gender="male", guardian_name="G", guardian_contact="0800000001")
    student_b = Student(school_id=second_school.id, student_id="STU-0001", first_name="B", last_name="Two",
                         gender="male", guardian_name="G", guardian_contact="0800000002")
    db.session.add_all([student_a, student_b])
    db.session.flush()

    p1 = Payment(school_id=school.id, student_id=student_a.id, collector_id=super_admin.id,
                 receipt_number=Payment.generate_receipt_number(school.id), amount=100,
                 payment_type=PaymentType.WEEKLY, payment_date=date.today())
    p2 = Payment(school_id=second_school.id, student_id=student_b.id, collector_id=super_admin.id,
                 receipt_number=Payment.generate_receipt_number(second_school.id), amount=100,
                 payment_type=PaymentType.WEEKLY, payment_date=date.today())
    db.session.add_all([p1, p2])
    db.session.commit()  # must NOT raise IntegrityError

    assert p1.receipt_number == p2.receipt_number  # same numbering, different schools - both valid
    assert p1.school_id != p2.school_id

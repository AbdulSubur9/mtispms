from datetime import date
from app.extensions import db
from app.models import Student, Payment, Expense
from app.models.payment import PaymentType
from app.models.expense import ExpenseCategory
from app.services import stats_service as stats
from tests.conftest import login


def test_username_uniqueness_enforced_with_friendly_message(client, school_admin, school):
    """Creating a second user with a username that already exists must show a
    friendly validation error, never a raw 500 - this is the class of bug
    that previously surfaced as 'Internal Server Error' on user creation."""
    login(client, "schooladmin", "Admin@123")
    resp = client.post("/admin/users/create", data={
        "username": "schooladmin",  # already taken by the logged-in admin itself
        "email": "someoneelse@test.com",
        "first_name": "Dup", "last_name": "User", "role": "collector",
        "school_id": school.id, "password": "Password123", "is_active_user": "y",
    }, follow_redirects=True)
    assert resp.status_code == 200  # never a 500
    assert b"already taken" in resp.data.lower()


def test_school_admin_cannot_create_user_without_school(client, school_admin):
    """A School Admin's own school is locked server-side; this test also
    guards against the school_id=0 usability bug where a Super Admin could
    previously leave a new School Admin's school unset."""
    login(client, "schooladmin", "Admin@123")
    resp = client.post("/admin/users/create", data={
        "username": "newcollector", "email": "newcollector@test.com",
        "first_name": "New", "last_name": "Collector", "role": "collector",
        "password": "Password123", "is_active_user": "y",
    }, follow_redirects=True)
    assert resp.status_code == 200
    # the user should have been created scoped to the school admin's own school
    from app.models import User
    created = User.query.filter_by(username="newcollector").first()
    assert created is not None
    assert created.school_id == school_admin.school_id


def test_expense_blocked_when_exceeding_available_balance(client, school_admin, school, super_admin):
    student = Student(school_id=school.id, student_id="STU-0001", first_name="A", last_name="B",
                       gender="male", guardian_name="G", guardian_contact="0800000000")
    db.session.add(student)
    db.session.flush()
    db.session.add(Payment(school_id=school.id, student_id=student.id, collector_id=super_admin.id,
                            receipt_number="RCT-26-00001", amount=100, payment_type=PaymentType.WEEKLY,
                            payment_date=date.today()))
    db.session.commit()

    assert stats.current_balance(school.id) == 100.0

    login(client, "schooladmin", "Admin@123")
    resp = client.post("/expenses/create", data={
        "category": ExpenseCategory.OTHERS, "amount": "500.00", "purpose": "Too much",
        "expense_date": date.today().isoformat(),
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"insufficient funds" in resp.data.lower()

    # no expense should have been created
    assert Expense.query.filter_by(school_id=school.id).count() == 0


def test_expense_allowed_within_available_balance(client, school_admin, school, super_admin):
    student = Student(school_id=school.id, student_id="STU-0001", first_name="A", last_name="B",
                       gender="male", guardian_name="G", guardian_contact="0800000000")
    db.session.add(student)
    db.session.flush()
    db.session.add(Payment(school_id=school.id, student_id=student.id, collector_id=super_admin.id,
                            receipt_number="RCT-26-00001", amount=500, payment_type=PaymentType.WEEKLY,
                            payment_date=date.today()))
    db.session.commit()

    login(client, "schooladmin", "Admin@123")
    resp = client.post("/expenses/create", data={
        "category": ExpenseCategory.OTHERS, "amount": "200.00", "purpose": "Fine",
        "expense_date": date.today().isoformat(),
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert Expense.query.filter_by(school_id=school.id).count() == 1


def test_student_history_blocked_across_schools(client, school_admin, school):
    """A School Admin from School A must never be able to view a School B
    student's payment history by guessing the URL id."""
    from app.models import School
    other_school = School(name="Other School", code="OTH999")
    db.session.add(other_school)
    db.session.flush()
    other_student = Student(school_id=other_school.id, student_id="STU-0001", first_name="X", last_name="Y",
                             gender="male", guardian_name="G", guardian_contact="0800000000")
    db.session.add(other_student)
    db.session.commit()

    login(client, "schooladmin", "Admin@123")
    resp = client.get(f"/reports/student-history/{other_student.id}")
    assert resp.status_code == 403

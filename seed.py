"""
Seed script for MT-ISPMS.

Usage:
    python seed.py
or, once the app is installed:
    flask seed

Seeds TWO schools on purpose (not one) - a second school whose students,
payments and expenses independently start from #0001 is exactly the
scenario that used to crash with an IntegrityError before the multi-tenant
uniqueness fix (see Student/Payment/Expense composite unique constraints).
Running this seed script successfully is itself a regression check for
that bug.
"""
import os
import random
from datetime import date, timedelta

from app import create_app
from app.extensions import db
from app.models import (
    School, User, Student, ClassRoom, Payment, Expense, AuditLog, Notification,
    SchoolPaymentType, Attendance, StudentApplication,
)
from app.models.user import Role
from app.models.payment import PaymentType
from app.models.expense import ExpenseCategory
from app.models.payment_type import PaymentFrequency
from app.models.attendance import AttendanceStatus


FIRST_NAMES = ["Ahmad", "Ibrahim", "Yusuf", "Aisha", "Fatima", "Zainab", "Umar", "Bilal",
               "Maryam", "Khadija", "Hassan", "Hussain", "Amina", "Musa", "Sulaiman"]
LAST_NAMES = ["Bello", "Suleiman", "Abdullahi", "Yakubu", "Garba", "Musa", "Aliyu",
              "Mohammed", "Ibrahim", "Sani", "Umar", "Lawal"]


def _make_user(username, email, first, last, role, school_id, password):
    u = User(
        username=username, email=email, first_name=first, last_name=last,
        role=role, school_id=school_id, is_active_user=True,
    )
    u.set_password(password)
    db.session.add(u)
    return u


def _seed_school(name, code, address, phone, email, admin_username, admin_password,
                  student_count, payment_count, expense_count):
    school = School(name=name, code=code, address=address, phone=phone, email=email, is_active=True)
    db.session.add(school)
    db.session.flush()

    admin = _make_user(admin_username, email, "School", "Admin", Role.SCHOOL_ADMIN, school.id, admin_password)
    accountant = _make_user(f"{admin_username}_accountant", f"accountant.{email}", "Fatima", "Nuhu",
                             Role.ACCOUNTANT, school.id, "Account@123")
    collector = _make_user(f"{admin_username}_collector", f"collector.{email}", "Bilal", "Sani",
                            Role.COLLECTOR, school.id, "Collect@123")
    teacher = _make_user(f"{admin_username}_teacher", f"teacher.{email}", "Musa", "Aliyu",
                          Role.TEACHER, school.id, "Teach@123")
    db.session.flush()

    classroom = ClassRoom(school_id=school.id, name="Hifz Class A", description="Demo class", teacher_id=teacher.id)
    db.session.add(classroom)
    db.session.flush()

    # Custom payment types for this school (item 6)
    for pt_name, freq, amt in [("Saturday Payment", PaymentFrequency.WEEKLY, 20),
                                ("First Term Fees", PaymentFrequency.TERMLY, 300)]:
        db.session.add(SchoolPaymentType(school_id=school.id, name=pt_name, frequency=freq, amount=amt))

    # Every school independently starts its numbering at #0001 - this is the
    # exact scenario that used to collide under the old global-unique schema.
    students = []
    for i in range(1, student_count + 1):
        s = Student(
            school_id=school.id,
            student_id=Student.generate_student_id(school.id),
            first_name=random.choice(FIRST_NAMES),
            last_name=random.choice(LAST_NAMES),
            gender=random.choice(["male", "female"]),
            date_of_birth=date(2012, 1, 1) + timedelta(days=random.randint(0, 2000)),
            guardian_name=f"{random.choice(LAST_NAMES)} {random.choice(FIRST_NAMES)}",
            guardian_contact=f"+233-24{random.randint(1000000, 9999999)}",
            class_id=classroom.id,
            admission_date=date.today() - timedelta(days=random.randint(30, 900)),
            status="active",
        )
        db.session.add(s)
        db.session.flush()
        students.append(s)

    for _ in range(payment_count):
        student = random.choice(students)
        db.session.add(Payment(
            school_id=school.id, student_id=student.id, collector_id=collector.id,
            receipt_number=Payment.generate_receipt_number(school.id),
            amount=random.choice([20, 50, 100, 300]),
            payment_type=random.choice(PaymentType.ALL),
            payment_date=date.today() - timedelta(days=random.randint(0, 60)),
            remarks="Seed data",
        ))
        db.session.flush()

    for _ in range(expense_count):
        db.session.add(Expense(
            school_id=school.id,
            reference_number=Expense.generate_reference_number(school.id),
            amount=random.choice([50, 100, 200, 400]),
            purpose=random.choice(["Stationery purchase", "Electricity bill", "Teacher salary"]),
            category=random.choice(ExpenseCategory.ALL),
            paid_to="Vendor / Staff", approved_by=admin.full_name, recorded_by_id=accountant.id,
            expense_date=date.today() - timedelta(days=random.randint(0, 60)),
            remarks="Seed data",
        ))
        db.session.flush()

    # A day of attendance for the demo class
    for s in students[: min(5, len(students))]:
        db.session.add(Attendance(
            school_id=school.id, class_id=classroom.id, student_id=s.id, teacher_id=teacher.id,
            attendance_date=date.today(), status=random.choice(AttendanceStatus.ALL),
        ))

    # A pending application
    db.session.add(StudentApplication(
        school_id=school.id, full_name="New Applicant Child", gender="male",
        guardian_name="Prospective Guardian", guardian_phone="+233-200000000",
        submitted_by_id=admin.id, application_date=date.today(),
    ))

    db.session.add(Notification(
        school_id=school.id, title="Welcome to MT-ISPMS",
        message="Your Madrassa payment management system is ready to use.", category="info",
    ))

    return school, admin


def run_seed():
    db.drop_all()
    db.create_all()

    super_admin = _make_user("admin", "admin@mtispms.local", "System", "Administrator",
                              Role.SUPER_ADMIN, None, "admin123")
    db.session.flush()

    school_a, admin_a = _seed_school(
        "Markaz Al-Huda Madrassa", "MAH001", "12 Islamiyya Road, Kano",
        "+234-800-000-0000", "schooladmin@markazalhuda.org", "schooladmin", "Admin@123",
        student_count=40, payment_count=150, expense_count=40,
    )
    school_b, admin_b = _seed_school(
        "Nur Ul-Islam Madrassa", "NUI002", "45 Faisal Street, Kaduna",
        "+234-800-111-1111", "schooladmin@nurulislam.org", "schooladmin2", "Admin@123",
        student_count=15, payment_count=30, expense_count=10,
    )

    db.session.commit()

    AuditLog.log("user_created", description="Database seeded with demo data", user=super_admin)

    print("Seed complete - two independent schools created (regression check for the")
    print("multi-tenant ID-collision bug: both schools' students/receipts start at #0001).")
    print()
    print("Super Admin login       -> username: admin           | password: admin123")
    print(f"School A ({school_a.name}) admin -> username: schooladmin    | password: Admin@123")
    print(f"School B ({school_b.name}) admin -> username: schooladmin2   | password: Admin@123")
    print("(each school also has its own _accountant / _collector / _teacher accounts, password Account@123 / Collect@123 / Teach@123)")


if __name__ == "__main__":
    app = create_app(os.environ.get("FLASK_ENV", "development"))
    with app.app_context():
        run_seed()

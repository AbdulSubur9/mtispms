"""
Seed script for MT-ISPMS.

Usage:
    python seed.py
or, once the app is installed:
    flask seed
"""
import os
import random
from datetime import date, timedelta

from app import create_app
from app.extensions import db
from app.models import (
    School, User, Student, ClassRoom, Payment, Expense, AuditLog, Notification
)
from app.models.user import Role
from app.models.payment import PaymentType
from app.models.expense import ExpenseCategory


FIRST_NAMES = ["Ahmad", "Ibrahim", "Yusuf", "Aisha", "Fatima", "Zainab", "Umar", "Bilal",
               "Maryam", "Khadija", "Hassan", "Hussain", "Amina", "Musa", "Sulaiman"]
LAST_NAMES = ["Bello", "Suleiman", "Abdullahi", "Yakubu", "Garba", "Musa", "Aliyu",
              "Mohammed", "Ibrahim", "Sani", "Umar", "Lawal"]


def run_seed():
    db.drop_all()
    db.create_all()

    # ---- School ----
    school = School(
        name="Markaz Al-Huda Madrassa",
        code="MAH001",
        address="12 Islamiyya Road, Kano",
        phone="+234-800-000-0000",
        email="info@markazalhuda.org",
        is_active=True,
    )
    db.session.add(school)
    db.session.flush()

    second_school = School(
        name="Nur Ul-Islam Madrassa",
        code="NUI002",
        address="45 Faisal Street, Kaduna",
        phone="+234-800-111-1111",
        email="info@nurulislam.org",
        is_active=True,
    )
    db.session.add(second_school)
    db.session.flush()

    # ---- Users ----
    def make_user(username, email, first, last, role, school_id, password="admin123"):
        u = User(
            username=username, email=email, first_name=first, last_name=last,
            role=role, school_id=school_id, is_active_user=True,
        )
        u.set_password(password)
        db.session.add(u)
        return u

    super_admin = make_user("admin", "admin@mtispms.local", "System", "Administrator",
                             Role.SUPER_ADMIN, None, password="admin123")

    school_admin = make_user("schooladmin", "admin@markazalhuda.org", "Umar", "Farouk",
                              Role.SCHOOL_ADMIN, school.id, password="Admin@123")
    accountant = make_user("accountant", "accountant@markazalhuda.org", "Fatima", "Nuhu",
                            Role.ACCOUNTANT, school.id, password="Account@123")
    collector1 = make_user("collector1", "collector1@markazalhuda.org", "Bilal", "Sani",
                            Role.COLLECTOR, school.id, password="Collect@123")
    collector2 = make_user("collector2", "collector2@markazalhuda.org", "Amina", "Garba",
                            Role.COLLECTOR, school.id, password="Collect@123")
    teacher = make_user("teacher1", "teacher1@markazalhuda.org", "Musa", "Aliyu",
                         Role.TEACHER, school.id, password="Teach@123")

    db.session.flush()

    # ---- Classes ----
    class_names = ["Hifz Class A", "Hifz Class B", "Tajweed Beginners", "Arabic Grammar", "Qaida Class"]
    classes = []
    for i, name in enumerate(class_names):
        c = ClassRoom(
            school_id=school.id, name=name, description=f"{name} - MT-ISPMS demo class",
            teacher_id=teacher.id if i == 0 else None,
        )
        db.session.add(c)
        classes.append(c)
    db.session.flush()

    # ---- Students ----
    students = []
    for i in range(1, 41):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        s = Student(
            school_id=school.id,
            student_id=f"STU-{i:04d}",
            first_name=first,
            last_name=last,
            gender=random.choice(["male", "female"]),
            date_of_birth=date(2012, 1, 1) + timedelta(days=random.randint(0, 2000)),
            guardian_name=f"{random.choice(LAST_NAMES)} {random.choice(FIRST_NAMES)}",
            guardian_contact=f"+234-70{random.randint(10000000, 99999999)}",
            class_id=random.choice(classes).id,
            admission_date=date.today() - timedelta(days=random.randint(30, 900)),
            status="active",
        )
        db.session.add(s)
        students.append(s)
    db.session.flush()

    # ---- Payments ----
    collectors = [collector1, collector2]
    receipt_counter = 1
    for _ in range(150):
        student = random.choice(students)
        collector = random.choice(collectors)
        p = Payment(
            school_id=school.id,
            student_id=student.id,
            collector_id=collector.id,
            receipt_number=f"RCT-{date.today().strftime('%y')}-{receipt_counter:05d}",
            amount=random.choice([500, 1000, 1500, 2000, 5000]),
            payment_type=random.choice(PaymentType.ALL),
            payment_date=date.today() - timedelta(days=random.randint(0, 60)),
            remarks="Seed data",
        )
        receipt_counter += 1
        db.session.add(p)

    # ---- Expenses ----
    ref_counter = 1
    for _ in range(40):
        e = Expense(
            school_id=school.id,
            reference_number=f"EXP-{date.today().strftime('%y')}-{ref_counter:05d}",
            amount=random.choice([2000, 5000, 10000, 15000, 25000]),
            purpose=random.choice([
                "Monthly teacher salary", "Stationery purchase", "Electricity bill",
                "Water bill", "Classroom maintenance", "Transportation for event",
                "Building project materials", "Food for students", "Miscellaneous",
            ]),
            category=random.choice(ExpenseCategory.ALL),
            paid_to="Vendor / Staff",
            approved_by=school_admin.full_name,
            recorded_by_id=accountant.id,
            expense_date=date.today() - timedelta(days=random.randint(0, 60)),
            remarks="Seed data",
        )
        ref_counter += 1
        db.session.add(e)

    # ---- Notifications ----
    db.session.add(Notification(
        school_id=school.id, title="Welcome to MT-ISPMS",
        message="Your Madrassa payment management system is ready to use.",
        category="info",
    ))

    db.session.commit()

    AuditLog.log("user_created", description="Database seeded with demo data", user=super_admin)

    print("Seed complete.")
    print("Super Admin login -> username: admin | password: admin123")
    print(f"School Admin login -> username: schooladmin | password: Admin@123 (school: {school.name})")
    print("Accountant login -> username: accountant | password: Account@123")
    print("Collector logins -> collector1 / collector2 | password: Collect@123")
    print("Teacher login -> username: teacher1 | password: Teach@123")


if __name__ == "__main__":
    app = create_app(os.environ.get("FLASK_ENV", "development"))
    with app.app_context():
        run_seed()

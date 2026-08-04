from datetime import datetime, date
from app.extensions import db


class ExpenseCategory:
    SALARY = "salary"
    STATIONERY = "stationery"
    ELECTRICITY = "electricity"
    WATER = "water"
    MAINTENANCE = "maintenance"
    TRANSPORTATION = "transportation"
    BUILDING_PROJECT = "building_project"
    FOOD = "food"
    OTHERS = "others"

    ALL = [SALARY, STATIONERY, ELECTRICITY, WATER, MAINTENANCE, TRANSPORTATION, BUILDING_PROJECT, FOOD, OTHERS]
    LABELS = {
        SALARY: "Salary",
        STATIONERY: "Stationery",
        ELECTRICITY: "Electricity",
        WATER: "Water",
        MAINTENANCE: "Maintenance",
        TRANSPORTATION: "Transportation",
        BUILDING_PROJECT: "Building Project",
        FOOD: "Food",
        OTHERS: "Others",
    }


class Expense(db.Model):
    __tablename__ = "expenses"
    __table_args__ = (
        db.UniqueConstraint("school_id", "reference_number", name="uq_expenses_school_reference_number"),
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)

    reference_number = db.Column(db.String(30), nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    purpose = db.Column(db.String(250), nullable=False)
    category = db.Column(db.String(30), nullable=False, default=ExpenseCategory.OTHERS)
    paid_to = db.Column(db.String(150))
    approved_by = db.Column(db.String(150))
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receipt_file = db.Column(db.String(250))
    expense_date = db.Column(db.Date, default=date.today, nullable=False)
    remarks = db.Column(db.String(250))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def category_label(self):
        return ExpenseCategory.LABELS.get(self.category, self.category)

    @staticmethod
    def generate_reference_number(school_id):
        """Generate the next EXP-YY-NNNNN reference number, unique within this
        school (scanning all existing numbers rather than trusting the last
        row - see Payment.generate_receipt_number for rationale)."""
        year = datetime.utcnow().strftime("%y")
        prefix = f"EXP-{year}-"
        existing = (
            db.session.query(Expense.reference_number)
            .filter(Expense.school_id == school_id, Expense.reference_number.like(f"{prefix}%"))
            .all()
        )
        max_num = 0
        for (ref,) in existing:
            try:
                num = int(ref.split("-")[-1])
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                continue
        return f"{prefix}{max_num + 1:05d}"

    def __repr__(self):
        return f"<Expense {self.reference_number} {self.amount}>"

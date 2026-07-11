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

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)

    reference_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
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
        last = (
            Expense.query.filter_by(school_id=school_id)
            .order_by(Expense.id.desc())
            .first()
        )
        next_num = 1
        if last and last.reference_number and "-" in last.reference_number:
            try:
                next_num = int(last.reference_number.split("-")[-1]) + 1
            except ValueError:
                next_num = Expense.query.filter_by(school_id=school_id).count() + 1
        year = datetime.utcnow().strftime("%y")
        return f"EXP-{year}-{next_num:05d}"

    def __repr__(self):
        return f"<Expense {self.reference_number} {self.amount}>"

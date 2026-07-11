from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import SelectField, DecimalField, DateField, StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional, Length
from app.models.expense import ExpenseCategory


class ExpenseForm(FlaskForm):
    category = SelectField(
        "Category",
        choices=[(c, ExpenseCategory.LABELS[c]) for c in ExpenseCategory.ALL],
        validators=[DataRequired()],
    )
    amount = DecimalField("Amount", places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    purpose = StringField("Purpose", validators=[DataRequired(), Length(max=250)])
    paid_to = StringField("Paid To", validators=[Optional(), Length(max=150)])
    approved_by = StringField("Approved By", validators=[Optional(), Length(max=150)])
    expense_date = DateField("Date", validators=[DataRequired()])
    remarks = TextAreaField("Remarks", validators=[Optional(), Length(max=250)])
    receipt_file = FileField("Receipt Upload", validators=[FileAllowed(["png", "jpg", "jpeg", "gif", "pdf"], "Images or PDF only")])
    submit = SubmitField("Save Expense")

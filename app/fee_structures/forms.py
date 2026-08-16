from flask_wtf import FlaskForm
from wtforms import DecimalField, SelectField, DateField, BooleanField, StringField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange


class FeeStructureForm(FlaskForm):
    class_id = SelectField("Class", coerce=int, validators=[DataRequired()])
    academic_year_id = SelectField("Academic Year", coerce=int, validators=[DataRequired()])
    term_id = SelectField("Term", coerce=int, validators=[DataRequired()])
    payment_type_id = SelectField("Payment Type", coerce=int, validators=[DataRequired()])
    amount = DecimalField("Amount (GH₵)", validators=[DataRequired(), NumberRange(min=0)], places=2)
    due_date = DateField("Due Date", validators=[Optional()], format="%Y-%m-%d")
    is_mandatory = BooleanField("Mandatory Fee", default=True)
    is_active = BooleanField("Active", default=True)
    notes = StringField("Notes", validators=[Optional()])
    submit = SubmitField("Save")

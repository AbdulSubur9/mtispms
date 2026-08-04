from flask_wtf import FlaskForm
from wtforms import SelectField, DecimalField, DateField, StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional, Length
from app.models.payment import PaymentType


class PaymentForm(FlaskForm):
    student_id = SelectField("Student", coerce=int, validators=[DataRequired()])
    payment_type = SelectField(
        "Payment Type",
        choices=[(t, PaymentType.LABELS[t]) for t in PaymentType.ALL],
        validators=[DataRequired()],
    )
    custom_payment_type_id = SelectField("Custom Payment Type (optional)", coerce=int, validators=[Optional()])
    amount = DecimalField("Amount", places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    payment_date = DateField("Payment Date", validators=[DataRequired()])
    remarks = TextAreaField("Remarks", validators=[Optional(), Length(max=250)])
    submit = SubmitField("Record Payment")


class VoidPaymentForm(FlaskForm):
    void_reason = StringField("Reason for Voiding", validators=[DataRequired(), Length(max=250)])
    submit = SubmitField("Void Payment")

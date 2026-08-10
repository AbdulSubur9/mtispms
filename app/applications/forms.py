from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Optional, Length


class StudentApplicationForm(FlaskForm):
    full_name = StringField("Student Full Name", validators=[DataRequired(), Length(max=160)])
    gender = SelectField("Gender", choices=[("male", "Male"), ("female", "Female")], validators=[DataRequired()])
    date_of_birth = DateField("Date of Birth", validators=[Optional()])
    previous_school = StringField("Previous School", validators=[Optional(), Length(max=150)])
    address = TextAreaField("Address", validators=[Optional(), Length(max=250)])

    guardian_name = StringField("Parent/Guardian Name", validators=[DataRequired(), Length(max=150)])
    guardian_phone = StringField("Parent/Guardian Phone", validators=[DataRequired(), Length(max=30)])
    guardian_occupation = StringField("Occupation", validators=[Optional(), Length(max=120)])
    guardian_address = TextAreaField("Guardian Address", validators=[Optional(), Length(max=250)])

    emergency_contact_name = StringField("Emergency Contact Name", validators=[Optional(), Length(max=150)])
    emergency_contact_phone = StringField("Emergency Contact Phone", validators=[Optional(), Length(max=30)])
    emergency_contact_relationship = StringField("Relationship", validators=[Optional(), Length(max=80)])

    has_medical_condition = BooleanField("Student has a medical condition")
    medical_condition_details = TextAreaField(
        "Medical Condition Details", validators=[Optional(), Length(max=500)]
    )

    declaration_accepted = BooleanField(
        "I declare that the information provided is true and accurate to the best of my knowledge",
        validators=[DataRequired(message="The declaration must be accepted to submit an application.")],
    )

    submit = SubmitField("Submit Application")

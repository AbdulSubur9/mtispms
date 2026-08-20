from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SelectField, TextAreaField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Optional, Length, Email, ValidationError


class ParentCreateForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired(), Length(max=80)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(max=80)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    phone = StringField("Phone", validators=[DataRequired(), Length(max=30)])
    alternative_phone = StringField("Alternative Phone", validators=[Optional(), Length(max=30)])
    relationship = SelectField(
        "Relationship",
        choices=[("Father", "Father"), ("Mother", "Mother"), ("Guardian", "Guardian"), ("Other", "Other")],
        default="Guardian",
    )
    occupation = StringField("Occupation", validators=[Optional(), Length(max=100)])
    address = TextAreaField("Address", validators=[Optional(), Length(max=250)])
    emergency_contact_name = StringField("Emergency Contact Name", validators=[Optional(), Length(max=120)])
    emergency_contact = StringField("Emergency Contact Phone", validators=[Optional(), Length(max=30)])
    submit = SubmitField("Create Parent Account")

    def validate_email(self, field):
        from app.models import User
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("A user with this email already exists.")


class ParentImportForm(FlaskForm):
    file = FileField("Excel File", validators=[DataRequired(), FileAllowed(["xlsx", "xls"], "Excel files only")])
    submit = SubmitField("Import")

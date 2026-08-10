from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SelectField, DateField, SubmitField
from wtforms.validators import DataRequired, Optional, Length


class StudentForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired(), Length(max=80)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(max=80)])
    gender = SelectField("Gender", choices=[("male", "Male"), ("female", "Female")], validators=[DataRequired()])
    date_of_birth = DateField("Date of Birth", validators=[Optional()])
    guardian_name = StringField("Guardian Name", validators=[DataRequired(), Length(max=120)])
    guardian_contact = StringField("Guardian Contact", validators=[DataRequired(), Length(max=30)])
    class_id = SelectField("Class", coerce=int, validators=[Optional()])
    admission_date = DateField("Admission Date", validators=[Optional()])
    status = SelectField(
        "Status",
        choices=[("active", "Active"), ("inactive", "Inactive"), ("deactivated", "Deactivated")],
        validators=[DataRequired()],
    )
    photo = FileField("Photo", validators=[Optional(), FileAllowed(["png", "jpg", "jpeg", "gif"], "Images only")])
    submit = SubmitField("Save Student")


class StudentUploadForm(FlaskForm):
    file = FileField("Excel File", validators=[DataRequired(), FileAllowed(["xlsx", "xls"], "Excel files only")])
    submit = SubmitField("Upload")

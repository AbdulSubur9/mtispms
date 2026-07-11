from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, EqualTo
from app.models.user import Role


class SchoolForm(FlaskForm):
    name = StringField("School Name", validators=[DataRequired(), Length(max=150)])
    code = StringField("School Code", validators=[DataRequired(), Length(max=20)])
    address = StringField("Address", validators=[Optional(), Length(max=250)])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    email = StringField("Email", validators=[Optional(), Email()])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save School")


class UserForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=64)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    first_name = StringField("First Name", validators=[DataRequired(), Length(max=80)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(max=80)])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    role = SelectField("Role", choices=[(r, Role.LABELS[r]) for r in Role.ALL], validators=[DataRequired()])
    school_id = SelectField("School", coerce=int, validators=[Optional()])
    password = PasswordField("Password", validators=[Optional(), Length(min=8, message="Minimum 8 characters")])
    is_active_user = BooleanField("Active", default=True)
    submit = SubmitField("Save User")

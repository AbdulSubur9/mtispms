from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SelectField, PasswordField, BooleanField, SubmitField, DecimalField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional, EqualTo, ValidationError
from app.models.user import Role, User
from app.models.school import School
from app.models.payment_type import PaymentFrequency


class BrandingForm(FlaskForm):
    logo = FileField("School Logo", validators=[Optional(), FileAllowed(["png", "jpg", "jpeg"], "Images only")])
    motto = StringField("Motto", validators=[Optional(), Length(max=200)])
    website = StringField("Website", validators=[Optional(), Length(max=200)])
    document_header_text = StringField(
        "Extra Header Text (shown on printed documents)", validators=[Optional(), Length(max=250)]
    )
    document_footer_text = StringField(
        "Extra Footer Text (shown on printed documents)", validators=[Optional(), Length(max=250)]
    )
    submit = SubmitField("Save Branding")


class SchoolForm(FlaskForm):
    name = StringField("School Name", validators=[DataRequired(), Length(max=150)])
    code = StringField("School Code", validators=[DataRequired(), Length(max=20)])
    address = StringField("Address", validators=[Optional(), Length(max=250)])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    email = StringField("Email", validators=[Optional(), Email()])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save School")

    def __init__(self, *args, obj=None, **kwargs):
        super().__init__(*args, obj=obj, **kwargs)
        self._obj = obj

    def validate_code(self, field):
        code = field.data.strip().upper()
        query = School.query.filter(School.code == code)
        if self._obj is not None:
            query = query.filter(School.id != self._obj.id)
        if query.first():
            raise ValidationError("A school with this code already exists.")


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

    def __init__(self, *args, obj=None, **kwargs):
        """`obj` is the User being edited (None when creating). Kept so the
        uniqueness validators below can exclude the record's own row."""
        super().__init__(*args, obj=obj, **kwargs)
        self._obj = obj

    def validate_username(self, field):
        username = field.data.strip()
        query = User.query.filter(User.username == username)
        if self._obj is not None:
            query = query.filter(User.id != self._obj.id)
        if query.first():
            raise ValidationError("That username is already taken. Please choose another.")

    def validate_email(self, field):
        email = field.data.strip().lower()
        query = User.query.filter(User.email == email)
        if self._obj is not None:
            query = query.filter(User.id != self._obj.id)
        if query.first():
            raise ValidationError("That email address is already registered to another user.")

    def validate_school_id(self, field):
        """A non-super-admin role must always be tied to a real school.
        This is what previously let a Super Admin accidentally create a
        School Admin with no school assigned (school_id left at 0 / None),
        leaving that account unable to do anything once they logged in."""
        if self.role.data and self.role.data != Role.SUPER_ADMIN and not field.data:
            raise ValidationError("Please select a school for this role.")


class PaymentTypeForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=100)])
    frequency = SelectField(
        "Frequency", choices=[(f, PaymentFrequency.LABELS[f]) for f in PaymentFrequency.ALL],
        validators=[DataRequired()],
    )
    amount = DecimalField("Default Amount (optional)", places=2, validators=[Optional()])
    allow_custom_amount = BooleanField(
        "Allow collectors to enter a different amount", default=True,
        description="Turn off to lock collectors to the exact default amount above (prevents mis-keyed fees).",
    )
    description = TextAreaField("Description", validators=[Optional(), Length(max=250)])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save Payment Type")

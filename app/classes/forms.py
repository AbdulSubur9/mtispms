from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class ClassRoomForm(FlaskForm):
    name = StringField("Class Name", validators=[DataRequired(), Length(max=100)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=250)])
    teacher_id = SelectField("Teacher", coerce=int, validators=[Optional()])
    submit = SubmitField("Save Class")

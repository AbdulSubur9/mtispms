from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, DecimalField, TextAreaField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class SubjectForm(FlaskForm):
    name = StringField("Subject Name", validators=[DataRequired(), Length(max=100)])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save Subject")


class ExamForm(FlaskForm):
    name = StringField("Examination Name", validators=[DataRequired(), Length(max=150)])
    class_id = SelectField("Class", coerce=int, validators=[DataRequired()])
    exam_date = DateField("Exam Date", validators=[Optional()])
    submit = SubmitField("Create Examination")


class GradingBandForm(FlaskForm):
    grade = StringField("Grade", validators=[DataRequired(), Length(max=5)])
    min_percentage = DecimalField("Min %", places=2, validators=[DataRequired(), NumberRange(min=0, max=100)])
    max_percentage = DecimalField("Max %", places=2, validators=[DataRequired(), NumberRange(min=0, max=100)])
    remark = StringField("Remark", validators=[Optional(), Length(max=100)])
    submit = SubmitField("Save Grade Band")

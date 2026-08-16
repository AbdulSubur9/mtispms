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
    academic_year_id = SelectField("Academic Year", coerce=int, validators=[DataRequired()])
    term_id = SelectField("Term", coerce=int, validators=[DataRequired()])
    exam_type = SelectField(
        "Type", choices=[("Examination", "Examination"), ("Test", "Test"), ("Quiz", "Quiz")],
        default="Examination", validators=[DataRequired()],
    )
    start_date = DateField("Start Date", validators=[Optional()])
    end_date = DateField("End Date", validators=[Optional()])
    description = TextAreaField("Description", validators=[Optional(), Length(max=2000)])
    submit = SubmitField("Create Examination")


class GradingBandForm(FlaskForm):
    grade = StringField("Grade", validators=[DataRequired(), Length(max=5)])
    min_percentage = DecimalField("Min %", places=2, validators=[DataRequired(), NumberRange(min=0, max=100)])
    max_percentage = DecimalField("Max %", places=2, validators=[DataRequired(), NumberRange(min=0, max=100)])
    remark = StringField("Remark", validators=[Optional(), Length(max=100)])
    submit = SubmitField("Save Grade Band")

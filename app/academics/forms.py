from flask_wtf import FlaskForm
from wtforms import StringField, DateField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Optional


class AcademicYearForm(FlaskForm):
    name = StringField("Academic Year Name", validators=[DataRequired()])
    start_date = DateField("Start Date", validators=[DataRequired()], format="%Y-%m-%d")
    end_date = DateField("End Date", validators=[DataRequired()], format="%Y-%m-%d")
    is_active = BooleanField("Active", default=True)
    is_current = BooleanField("Set as Current Year")
    submit = SubmitField("Save")


class TermForm(FlaskForm):
    name = StringField("Term Name", validators=[DataRequired()])
    start_date = DateField("Start Date", validators=[DataRequired()], format="%Y-%m-%d")
    end_date = DateField("End Date", validators=[DataRequired()], format="%Y-%m-%d")
    is_active = BooleanField("Active", default=True)
    is_current = BooleanField("Set as Current Term")
    submit = SubmitField("Save")

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import data_required


class NameForm(FlaskForm):
    name = StringField('What is your name?', validators=[data_required()])
    password = PasswordField('Password', validators=[data_required()])
    submit = SubmitField('Submit')


class BaseForm(FlaskForm):
    @classmethod
    def append_field(cls, name, field):
        setattr(cls, name, field)
        return cls


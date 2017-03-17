from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, TextAreaField, ValidationError
from wtforms.validators import DataRequired
from json import loads


class NameForm(FlaskForm):
    name = StringField('What is your name?', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Submit')


class BaseForm(FlaskForm):
    @classmethod
    def append_field(cls, name, field):
        setattr(cls, name, field)
        return cls


class GameTypeForm(FlaskForm):
    info = StringField('Info about the game configuration', validators=[DataRequired()])
    params = TextAreaField('Configuration parameters (in JSON string format)', validators=[
        DataRequired()])

    submit = SubmitField('Add Configuration')


    def validate_params(self, field):
        try:
            loads(field.data)
        except ValueError as ve:
            raise ValidationError('No valid JSON string in parameters.')

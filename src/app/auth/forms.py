from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import data_required, email, length, equal_to, regexp
from wtforms import ValidationError
from ..models import User


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[data_required, length(1, 64),
                                             email()])
    password = PasswordField('Password', validators=[data_required])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log In')


class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[data_required, length(1, 64), email])
    username = StringField('Username', validators=[
        data_required, length(1, 64), regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                             'Usernames must have only letters, '
                                             'numbers, dots or underscores')])
    password = PasswordField('Password', validators=[data_required, equal_to('password2',
                                                                             message='Password '
                                                                                     'must '
                                                                                     'match.')])
    password2 = PasswordField('Confirm password', validators=[data_required])
    submit = SubmitField('Register')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')

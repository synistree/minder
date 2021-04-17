from flask_wtf import FlaskForm

from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
    username = StringField('Username', [DataRequired(), Length(min=3, max=25)])
    password = PasswordField('Password', [DataRequired(), Length(min=6, max=200)])
    remember_me = BooleanField('Remember Me?', default=True)
    submit = SubmitField('Login')

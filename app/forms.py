from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from app.models import User


class RegisterForm(FlaskForm):
    username = StringField('Kullanıcı Adı', 
        validators=[DataRequired(message='Kullanıcı adı zorunludur'), 
                    Length(min=3, max=80, message='Kullanıcı adı 3-80 karakter olmalı')])
    email = StringField('E-posta', 
        validators=[DataRequired(message='E-posta zorunludur'), 
                    Email(message='Geçerli bir e-posta giriniz')])
    password = PasswordField('Şifre', 
        validators=[DataRequired(message='Şifre zorunludur'), 
                    Length(min=6, message='Şifre en az 6 karakter olmalı')])
    confirm_password = PasswordField('Şifreyi Tekrarla',
        validators=[DataRequired(message='Şifre tekrarı zorunludur'),
                    EqualTo('password', message='Şifreler eşleşmiyor')])
    submit = SubmitField('Kayıt Ol')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Bu kullanıcı adı zaten kullanılıyor. Farklı bir tane seç.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Bu e-posta zaten kayıtlı. Giriş yapmayı dene.')


class LoginForm(FlaskForm):
    email = StringField('E-posta', 
        validators=[DataRequired(), Email()])
    password = PasswordField('Şifre', 
        validators=[DataRequired()])
    remember = BooleanField('Beni Hatırla')
    submit = SubmitField('Giriş Yap')
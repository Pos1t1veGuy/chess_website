from django import forms
from django.forms.models import model_to_dict
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string
from django.core.mail import send_mail

from django.core.cache import cache
from email_validate import validate
from PIL import Image
from django.conf import settings

from AUTH.models import User


class LoginForm(forms.Form):
    email_or_username = forms.CharField(label='Почта или логин', max_length=254)
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput(attrs={'id': 'login_password'}))

    def clean(self):
        email_or_username = self.cleaned_data.get('email_or_username')
        password = self.cleaned_data.get('password')

        if email_or_username and password:
            if '@' == email_or_username[0]:
                self.user = authenticate(username=email_or_username[1:], password=password)
            elif '@' in email_or_username:
                self.user = authenticate(email=email_or_username, password=password)
            else:
                self.user = authenticate(username=email_or_username, password=password)

            if not self.user:
                raise ValidationError('Неправильные логин/почта или пароль')

        return self.cleaned_data

    def get_user(self):
        return self.user

class RegisterForm(forms.ModelForm):
    username = forms.CharField(label='Логин', max_length=254)
    email = forms.CharField(label='Почта', max_length=254)
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput(attrs={'id': 'register_password'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError('Этот логин уже занят')
        if not settings.MIN_USERNAME_LENGTH <= len(username) <= settings.MAX_USERNAME_LENGTH:
            raise ValidationError(f'Логин должен быть длинной от {settings.MIN_USERNAME_LENGTH} до {settings.MAX_USERNAME_LENGTH} символов')
        if not all([ char in settings.ENABLED_USERNAME_CHARS for char in username ]):
            raise ValidationError(f'Логин должен содержать только разрешенные символы [a-z] [A-Z] [0-9] [-] [_]')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not validate(email_address=email, check_blacklist=False, check_dns=False, check_smtp=False):
            raise ValidationError('Неправильная почта')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Эта почта уже используется')
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < settings.PASSWORD_MIN_LENGTH:
            raise ValidationError(f'Пароль должен быть минимум из {settings.PASSWORD_MIN_LENGTH} символов')
        if not all([ char in settings.ENABLED_PASSWORD_CHARS for char in password ]):
            raise ValidationError('Пароль должен содержать только символы [a-z] [A-Z] [0-9]')
        return password

    def send_code(self, email: str):
        code = get_random_string(length=4, allowed_chars='0123456789')
        cache.set(f'temp_code_{code}', {
            'type': 'form',
            'class_name': self.__class__.__name__,
            'class_path': 'AUTH.forms',
            'form_data': model_to_dict(self.instance, fields=['username', 'email', 'password']),
            'login_after': True,
        }, timeout=settings.REG_CODE_TIMEOUT)

        send_mail('Код подтверждения изменений профиля', f'Ваш код подтверждения: {code}', settings.EMAIL_HOST_USER, [email])

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class EditProfileForm(forms.ModelForm):
    username = forms.CharField(label='Логин', max_length=254)
    first_name = forms.CharField(label='Имя', max_length=254, required=False)
    last_name = forms.CharField(label='Фамилия', max_length=254, required=False)

    avatar = forms.ImageField(label='Аватар', max_length=254)
    email = forms.CharField(label='Почта', max_length=254)
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput(attrs={'id': 'register_password', 'autocomplete': 'new-password'}), required=False)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'avatar', 'password']
        
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Этот логин уже занят')
        if not settings.MIN_USERNAME_LENGTH <= len(username) <= settings.MAX_USERNAME_LENGTH:
            raise ValidationError(f'Логин должен быть длинной от {settings.MIN_USERNAME_LENGTH} до {settings.MAX_USERNAME_LENGTH} символов')
        if not all([ char in settings.ENABLED_USERNAME_CHARS for char in username ]):
            raise ValidationError(f'Логин должен содержать только разрешенные символы [a-z] [A-Z] [0-9] [-] [_]')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Эта почта уже используется')
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < settings.PASSWORD_MIN_LENGTH:
            raise ValidationError(f'Пароль должен быть минимум из {settings.PASSWORD_MIN_LENGTH} символов')
        if not all([ char in settings.ENABLED_PASSWORD_CHARS for char in password ]):
            raise ValidationError('Пароль должен содержать только символы [a-z] [A-Z] [0-9]')
        return password

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')

        if avatar == self.initial.get('avatar'):
            return self.instance.avatar

        elif avatar:
            if not avatar.content_type in ['image/jpeg', 'image/png']:
                raise ValidationError('Поддерживаются только файлы JPEG/PNG')

            if avatar.size > settings.MAX_AVATAR_SIZE * 1024 * 1024:
                raise ValidationError(f'Файл слишком большой, максимум {settings.MAX_AVATAR_SIZE} MB')

            try:
                Image.open(avatar).verify()
            except Exception:
                raise ValidationError('Загрузите правильное изображение')

        return avatar

    def send_code(self, email: str):
        code = get_random_string(length=4, allowed_chars='0123456789')
        cache.set(f'temp_code_{code}', {
            'type': 'form',
            'class_name': self.__class__.__name__,
            'class_path': 'AUTH.forms',
            'form_data': model_to_dict(self.instance),
        }, timeout=settings.EP_CODE_TIMEOUT)

        send_mail('Код подтверждения изменений профиля', f'Ваш код подтверждения: {code}', settings.EMAIL_HOST_USER, [email])

    def save(self, commit=True):
        old_user = User.objects.get(pk=self.instance.pk)
        user = super().save(commit=False)

        if self.cleaned_data['password']:
            user.set_password(self.cleaned_data['password'])
        else:
            user.password = old_user.password

        if commit:
            user.save()
        return user
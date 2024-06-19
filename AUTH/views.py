from django.shortcuts import render, redirect
from django.urls import reverse, resolve, Resolver404
from django.http import HttpResponse, Http404

from django.contrib.auth.decorators import login_required
from django.views import View
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.conf import settings

from .models import User

from email_validate import validate
import secrets


class login_or_register(View):
    template_name = 'logorreg.html'

    def get(self, request):
        if request.META.get('HTTP_REFERER'):
            request.session['previous_path'] = '/'+'/'.join(request.META.get('HTTP_REFERER').split('/')[3:-1])
        return render(request, self.template_name, {'last_page': request.path})

    @method_decorator(csrf_protect)
    def post(self, request):
        Type = request.POST.get('type')

        if Type == 'auth':
            username_or_email = request.POST.get('email_or_username')
            password = request.POST.get('password')

            if username_or_email and password:
                if FormUtils.is_email(username_or_email):
                    user_exists = User.objects.filter(email=username_or_email).exists()
                    user = authenticate(request, email=username_or_email, password=password)

                    if user is not None:
                        login(request, user)
                        return self._redirect(request)

                    if user_exists:
                        return render(request, self.template_name, {'auth_error': f'Неправильный пароль'})
                    else:
                        return render(request, self.template_name, {'auth_error': f'Пользователь с именем {username_or_email} не существует'})
                else:
                    user_exists = User.objects.filter(username=username_or_email).exists()
                    user = authenticate(request, username=username_or_email, password=password)

                    if user is not None:
                        login(request, user)
                        return self._redirect(request)

                    if user_exists:
                        return render(request, self.template_name, {'auth_error': f'Неправильный пароль'})
                    else:
                        return render(request, self.template_name, {'auth_error': f'Пользователь с почтой {username_or_email} не существует'})
            else:
                return render(request, self.template_name, {'auth_error': f'Неправильные данные'})
        
        elif Type == 'reg':
            reg_timeout_sec = 300
            check_email = False
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')

            if username and email and password:
                if FormUtils.is_username(username):
                    if not User.objects.filter(username=username).exists():
                        if FormUtils.is_email(email):
                            if not User.objects.filter(email=email).exists():
                                if validate(email_address=email, smtp_from_address='questioner@card_questions.ru') or not check_email:
                                    # code = secrets.token_urlsafe(16)
                                    # cache.set(f'registration_code_{user.id}', code, timeout=reg_timeout_sec)
                                    user = User.objects.create_user(username=username, email=email, password=password)
                                    login(request, user)
                                    return self._redirect(request)
                                else:
                                    return render(request, self.template_name, {'reg_error': f'Почта {email} не существует.'})
                            else:
                                return render(request, self.template_name, {'reg_error': f'Почта {email} уже зарегестрирована.'})
                        else:
                            return render(request, self.template_name, {'reg_error': f'Неправильная почта {email}.'})
                    else:
                        return render(request, self.template_name, {'reg_error': f'Ник {username} уже используется.'})
                else:
                    return render(request, self.template_name, {'reg_error': f'Неправильный ник {username}. При составлении ника можно использовать a-z, A-Z, 0-9, _, -, при этом ник должен быть от 1 до 45 символов.'})

        else:
            return render(request, self.template_name, {'error': f'Неизвесный тип операции'})

    def _redirect(self, request):
        if request.session.get('previous_path'):
            path = request.session['previous_path'].split('?')[0]

            try:
                resolve(path)
                path_exists = True
            except Resolver404:
                path_exists = False

            if path in ['/account/hello', '', reverse('auth:auth')] or not path_exists:
                return redirect('chess:home')
            else:
                return redirect(path)

        return redirect('chess:home')


@login_required(login_url='chess:home')
def info(request):
    return account_info(request, request.user)

@login_required(login_url='chess:home')
def logout_view(request):
    logout(request)
    return redirect('chess:home')

def account_info(request, account_username: str):
    try:
        return render(request, 'account_info.html', {'user': request.user, 'account': User.objects.get(username=account_username)})
    except User.DoesNotExist:
        raise Http404('')


class FormUtils:
    def is_username(name: str) -> bool:
        if len(name) > settings.MAX_USERNAME_LENGTH or len(name) < settings.MIN_USERNAME_LENGTH:
            return False

        for char in name:
            if not char in settings.ENABLED_USERNAME_CHARS:
                return False

        return True
    
    def is_email(name: str) -> bool:
        return validate(email_address=name, check_blacklist=False, check_dns=False, check_smtp=False)
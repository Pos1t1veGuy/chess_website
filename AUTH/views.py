from django.shortcuts import render, redirect
from django.urls import reverse, resolve, Resolver404
from django.http import HttpResponse, Http404

from django.contrib.auth.decorators import login_required
from django.views import View
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile

from .models import User
from .forms import *

from importlib import import_module
from django.conf import settings
import secrets
import random
import os


def redirect_back(request, excluding_url: str = None):
    if 'previous_path' in request.session.keys():
        try:
            banned_urls = [reverse('chess:hello'), '', reverse('auth:code'), reverse('auth:auth'), excluding_url]
            if request.session['previous_path'] in banned_urls or request.session['previous_path'] + '/' in banned_urls:
                return redirect('chess:home')

            return redirect(request.session['previous_path'])

        except Resolver404:
            pass

    return redirect('chess:home')


class login_or_register(View):
    template_name = 'logorreg.html'

    def get(self, request):
        if request.META.get('HTTP_REFERER'):
            request.session['previous_path'] = '/'+'/'.join(request.META.get('HTTP_REFERER').split('/')[3:-1])

        type_ = request.GET.get('type', None)
        return render(request, self.template_name, {'login_form': LoginForm(), 'register_form': RegisterForm(), 'reg': type_ == 'register'})

    @method_decorator(csrf_protect)
    def post(self, request):
        type_ = request.POST.get('type')
        
        if type_ == 'auth':
            login_form = LoginForm(request.POST)

            if login_form.is_valid():
                user = login_form.get_user()
                if user:
                    login(request, user)
                    return redirect_back(request)

            return render(request, self.template_name, {
                'login_form': login_form,
                'register_form': RegisterForm(),
                'auth_error': 'Invalid login or password',
                'reg': False,
            })
        
        elif type_ == 'reg':
            register_form = RegisterForm(request.POST)

            if register_form.is_valid():
                register_form.send_code(request.POST['email'])
                return redirect('auth:code')

            return render(request, self.template_name, {'login_form': LoginForm(), 'register_form': register_form, 'reg': True})

        else:
            raise Http404('Unknown operation type')

class edit(View):
    @method_decorator(login_required(login_url='auth:auth'))
    def get(self, request):
        try:
            if request.META.get('HTTP_REFERER'):
                request.session['previous_path'] = '/'+'/'.join(request.META.get('HTTP_REFERER').split('/')[3:-1])

            return render(request, 'edit_profile.html', {'user': request.user, 'form': EditProfileForm(initial={
                'username': request.user.username,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
            }, instance=request.user)})
        except User.DoesNotExist:
            raise Http404('')

    @method_decorator(login_required(login_url='auth:auth'))
    @method_decorator(csrf_protect)
    def post(self, request):
        old_email = request.user.email
        ep_form = EditProfileForm(request.POST, request.FILES, instance=request.user)
        
        if (not request.POST.get('password', None) and
            request.POST.get('username', None) == request.user.username and
            request.POST.get('first_name', None) == request.user.first_name and
            request.POST.get('last_name', None) == request.user.last_name and
            request.POST.get('email', None) == request.user.email and
            request.POST.get('avatar', None) == request.user.avatar
            ):
            return redirect_back(request, reverse('auth:edit_profile'))

        elif ep_form.is_valid():
            if request.POST.get('password', None) != '' or request.POST.get('email', None) != old_email:
                request.session['ep_form'] = ep_form.serialize()
                ep_form.send_code(request.user.email)
                return redirect('auth:code')

            else:
                ep_form.save()
                return redirect_back(request, reverse('auth:edit_profile'))

        else:
            return render(request, 'edit_profile.html', {'user': request.user, 'form': ep_form})


class code(View):
    def get(self, request):
        if request.META.get('HTTP_REFERER'):
            request.session['previous_path'] = '/'+'/'.join(request.META.get('HTTP_REFERER').split('/')[3:-1])
            if request.session['previous_path'] == reverse('auth:auth'):
                request.session['previous_path'] = reverse('chess:home')
        try:
            return render(request, 'code_required.html', {'user': request.user})
        except User.DoesNotExist:
            raise Http404('')

    @method_decorator(csrf_protect)
    def post(self, request):
        code = request.POST.get('code')
        cache_data = cache.get(f'temp_code_{code}', None)
        if cache_data:
            if cache_data['type'] == 'form':
                form_module = import_module(cache_data['class_path'])
                data = cache_data['form_data']
                for key, value in data.items():
                    if isinstance(data[key], dict):
                        if list(data[key].keys())[0] == 'image':
                            file = data[key]['image']
                            bytes_ = open(settings.TEMP_MEDIA_DIR + file, 'rb').read()
                            io = BytesIO(bytes_)
                            io.seek(0)

                            data[key] = InMemoryUploadedFile(io, None, file, 'image/png', len(bytes_), None)
                            os.remove(settings.TEMP_MEDIA_DIR + file)

                FormObject = getattr(form_module, cache_data['class_name'])(data=data, instance=request.user)

                if FormObject.is_valid():
                    res = FormObject.save()

                    if 'login_after' in cache_data.keys():
                        if cache_data['login_after']:
                            login(request, res)

                    if 'redirect_after' in cache_data.keys():
                        return redirect(cache_data['redirect_after'])

                    return redirect_back(request)

        raise Http404('')


@login_required(login_url='auth:auth')
def info(request):
    return account_info(request, request.user.username)

@login_required(login_url='auth:auth')
def logout_view(request):
    logout(request)
    return redirect('chess:home')

def account_info(request, account_username: str):
    try:
        return render(request, 'account_info.html', {'user': request.user, 'account': User.objects.get(username=account_username)})
    except User.DoesNotExist:
        raise Http404('')
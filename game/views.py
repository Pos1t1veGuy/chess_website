from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from django.urls import reverse

from AUTH.models import User
import requests as rq, json


def home(request):
	return HttpResponse('home')

def leaders(request): # Доделать джаваскриптовую подгрузку списка
	leaders_url = request.build_absolute_uri(f'{reverse("api")}?key=leaders&portion={settings.LEADERS_PORTION}&index=0')
	first_portion = json.loads(rq.get(leaders_url).content)
	return render(request, 'leaders.html', {'user': request.user, 'users': User.objects.filter(username__in=first_portion), 'leaders_url': leaders_url[:-1]})

def game(request, game_id: int):
	return HttpResponse(f'game {game_id}')
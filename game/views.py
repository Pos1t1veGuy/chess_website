from django.shortcuts import render
from django.http import HttpResponse

from AUTH.models import User


def home(request):
	return HttpResponse('home')

def leaders(request):
	return render(request, 'leaders.html', {'user': request.user, 'users': User.objects.all()})

def game(request, game_id: int):
	return HttpResponse(f'game {game_id}')
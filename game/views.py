from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.conf import settings
from django.urls import reverse

from AUTH.models import User
from game.models import Game
import requests as rq, json


def home(request):
	return render(request, 'home.html', {'user': request.user})
def hello(request):
    return render(request, 'hello.html', {'user': request.user})

def leaders(request):
	leaders_url = request.build_absolute_uri(f'{reverse("api")}?key=leaders&portion={settings.LEADERS_PORTION}&index=0')
	first_portion = json.loads(rq.get(leaders_url).content)
	return render(request, 'leaders.html', {
		'user': request.user,
		'users': [ User.objects.get(username=user['username']) for user in first_portion ],
		'leaders_url': leaders_url[:-1]
	})

def game(request, game_id: int):
	game = get_object_or_404(Game, id=game_id)
	if request.user in game.players:
		try:
			return render(request, 'game.html', {
				'user': request.user,
				'game': game,
				'white_player_time': int(game.passed_time('white')),
				'black_player_time': int(game.passed_time('black')),
				'max_time': game.max_time
			})
		except ValueError as ve:
			if str(ve) == 'The game is ended':
				return info(request, game_id)
			else:
				raise ValueError(ve)
	else:
		return redirect('chess:info', game.id)

def info(request, game_id: int):
	game = get_object_or_404(Game, id=game_id)
	return render(request, 'game_info.html', {'user': request.user, 'game': game, 'white': game.white_player, 'black': game.black_player, 'max_time': game.max_time/60})
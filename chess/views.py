from typing import *

from django.shortcuts import render
from django.http import HttpResponse, Http404, FileResponse, JsonResponse
from django.views import View
from django.conf import settings
from django.shortcuts import get_object_or_404

from AUTH.models import User
from game.models import Game
import json
import random
import os


class api(View):
	def get(self, request):
		key = request.GET.get('key')
		match key:
			case 'leaders':
				order_by = json.loads(request.GET.get('order_by')) if request.GET.get('order_by') else None
				if order_by and isinstance(order_by, (list, tuple)):
					qs = User.objects.order_by(*order_by)
				elif order_by and isinstance(order_by, str):
					qs = User.objects.order_by(order_by)
				else:
					qs = User.objects.order_by('global_score')

				return self.objects_portion(request, [ {
					'username': user.username,
					'winrate': user.winrate,
					'games_count': user.games_count,
					'score': user.global_score
				} for user in sorted(qs, key=lambda user: (
					-user.winrate,
					-user.games_count,
					-user.global_score,
				)) ])

			case 'active_games':
				return self.objects_portion(request, Game.objects.filter(ended=False).order_by('playing').values_list(
					'id', 'start_time', 'white_player__username', 'black_player__username')
				)

			case 'users_queue':
				from chess.consumers import queue_consumers
				return self.objects_portion(request, [ {
					'username': user.username,
					'winrate': user.winrate,
					'games_count': user.games_count,
					'score': user.global_score
				} for user in queue_consumers ])

			case 'game':
				if 'id' in request.GET.keys():
					if str(request.GET['id']).isdigit():
						game = get_object_or_404(Game, id=int(request.GET['id']))
						return JsonResponse({
							'id': game.id,
							'start_time': str(game.start_time),
							'status': 0 if game.ended and not game.playing else (1 if not game.ended and not game.playing else 2),
							'winner': game.winner,
							'last_movement_time': str(game.last_movement_time),
							'board': game.movements[-1],

							'white_score': game.white_player_score,
							'white_passed_time': game.white_player_score,
							'destoyed_white_pieces': game.lost_pieces_by_color('white'),

							'black_score': game.black_player_score,
							'black_passed_time': game.black_player_score,
							'destoyed_white_pieces': game.lost_pieces_by_color('black'),
						})

		raise Http404('')

	def objects_portion(self, request, queryset: Union['QuerySet', list]) -> 'HttpResponse':
		portion = request.GET.get('portion')
		index = request.GET.get('index')
		if portion and index:
			if portion.isdigit() and index.isdigit():
				portion = int(portion)
				index = int(index)
				if 0 <= portion and 0 <= index:
					if User.objects.count() <= index:
						raise Http404('')
					elif User.objects.count() <= portion:
						return HttpResponse(json.dumps(list( queryset ), default=str))
					elif User.objects.count() <= index + portion:
						return HttpResponse(json.dumps(list( queryset[index:] ), default=str))
					else:
						return HttpResponse(json.dumps(list( queryset[index:index+portion] ), default=str))
		elif index:
			if index.isdigit():
				index = int(index)
				if 0 <= index <= User.objects.count():
					return HttpResponse(json.dumps( list(queryset)[index] ))

		raise Http404('')

def random_favicon(request):
	try:
		icons = os.listdir(settings.ICONS_DIR)
		if icons:
			return FileResponse(open(f'{settings.ICONS_DIR}/{random.choice(icons)}', 'rb'), content_type='image/x-icon')
		else:
			raise Http404("No icons found")
	except FileNotFoundError:
		raise Http404("Icon directory not found")
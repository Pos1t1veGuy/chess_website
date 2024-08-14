from typing import *

from django.shortcuts import render
from django.http import HttpResponse, Http404, FileResponse, JsonResponse
from django.views import View
from django.conf import settings
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

import json
import random
import os

from .serializers import UserSerializer, GameSerializer
from .models import User, Game


class api(APIView):
	def get(self, request):
		key = request.query_params.get('key')
		match key:
			case 'leaders':
				return self.get_leaders(request)
			case 'active_games':
				return self.get_active_games(request)
			case 'users_queue':
				return self.get_users_queue(request)
			case 'game':
				return self.get_game(request)
		return Response(status=status.HTTP_404_NOT_FOUND)

	def get_leaders(self, request):
		order_by = request.query_params.getlist('order_by') or ['global_score']
		users = User.objects.order_by(*order_by)
		users = sorted(users, key=lambda user: (
			-user.winrate,
			user.games_count,
			user.global_score,
		))[::-1]
		return self.objects_portion(request, users, UserSerializer)

	def get_active_games(self, request):
		games = Game.objects.filter(ended=False).order_by('playing')
		return self.objects_portion(request, games, GameSerializer)

	def get_users_queue(self, request):
		from chess.consumers import queue_consumers
		return self.objects_portion(request, [ con.user for con in queue_consumers ], UserSerializer)

	def get_game(self, request):
		game_id = request.query_params.get('id')
		if game_id and game_id.isdigit():
			game = get_object_or_404(Game, id=int(game_id))
			serializer = GameSerializer(game)
			return Response(serializer.data, status=status.HTTP_200_OK)
		return Response(status=status.HTTP_404_NOT_FOUND)

	def objects_portion(self, request, queryset, serializer_class):
		portion = request.query_params.get('portion')
		index = request.query_params.get('index')
		if portion and index and portion.isdigit() and index.isdigit():
			portion = int(portion)
			index = int(index)
			if 0 <= portion and 0 <= index:
				sliced_queryset = queryset[index:index+portion]
				serializer = serializer_class(sliced_queryset, many=True)
				return Response(serializer.data, status=status.HTTP_200_OK)
		elif index and index.isdigit():
			index = int(index)
			if 0 <= index < len(queryset):
				serializer = serializer_class(queryset[index], many=False)
				return Response(serializer.data, status=status.HTTP_200_OK)
		return Response(status=status.HTTP_404_NOT_FOUND)


def random_favicon(request):
	try:
		icons = os.listdir(settings.ICONS_DIR)
		if icons:
			return FileResponse(open(f'{settings.ICONS_DIR}/{random.choice(icons)}', 'rb'), content_type='image/x-icon')
		else:
			raise Http404("No icons found")
	except FileNotFoundError:
		raise Http404("Icon directory not found")
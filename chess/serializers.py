from typing import *

from rest_framework import serializers
from .models import User, Game


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'winrate', 'games_count', 'global_score']

class GameSerializer(serializers.ModelSerializer):
    white_player = serializers.CharField(source='white_player.username')
    black_player = serializers.CharField(source='black_player.username')
    white_passed_time = serializers.SerializerMethodField()
    black_passed_time = serializers.SerializerMethodField()
    destroyed_white_pieces = serializers.SerializerMethodField()
    destroyed_black_pieces = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = [
            'id', 'start_time', 'ended', 'playing', 'winner',
            'last_movement_time', 'white_player', 'black_player',
            'white_player_score', 'black_player_score', 'movements',

            'white_passed_time', 'black_passed_time', 'destroyed_white_pieces', 'destroyed_black_pieces'
        ]

    def get_white_passed_time(self, obj: 'Game') -> float:
        return obj.passed_time('white')

    def get_black_passed_time(self, obj: 'Game') -> float:
        return obj.passed_time('black')

    def get_destroyed_white_pieces(self, obj: 'Game') -> List[str]:
        return obj.lost_pieces_by_color('white')

    def get_destroyed_black_pieces(self, obj: 'Game') -> List[str]:
        return obj.lost_pieces_by_color('black')
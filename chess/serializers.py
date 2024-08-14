from rest_framework import serializers
from .models import User, Game

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'winrate', 'games_count', 'global_score']

class GameSerializer(serializers.ModelSerializer):
    white_player = serializers.CharField(source='white_player.username')
    black_player = serializers.CharField(source='black_player.username')

    class Meta:
        model = Game
        fields = [
            'id', 'start_time', 'ended', 'playing', 'winner',
            'last_movement_time', 'white_player', 'black_player',
            'white_player_score', 'black_player_score', 'movements'
        ]
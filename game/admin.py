from django.contrib import admin
from .models import Game

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['white_player', 'black_player', 'ended', 'created_at', 'winner']

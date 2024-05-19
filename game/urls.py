from django.contrib import admin
from django.urls import path, include

from django.shortcuts import redirect

from .views import home, leaders, game, info, hello


app_name = 'chess'
urlpatterns = [
    path('', home, name='home'),
    path('leaders/', leaders, name='leaders'),
    path('games/', lambda request: redirect('chess:home'), name='home_redirect'),
    path('games/<int:game_id>/', info, name='info'),
    path('games/<int:game_id>/play', game, name='game'),
    path('hello/', hello, name='hello'),
]
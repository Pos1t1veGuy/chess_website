from django.contrib import admin
from django.urls import path, include

from django.shortcuts import redirect

from .views import home, leaders, game


app_name = 'chess'
urlpatterns = [
    path('', home, name='home'),
    path('leaders/', leaders, name='leaders'),
    path('game/', lambda request: redirect('chess:home'), name='home_redirect'),
    path('game/<int:game_id>/', game, name='game'),
]
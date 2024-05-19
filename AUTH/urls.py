from django.contrib import admin
from django.urls import path, include

from .views import login_or_register, info, logout_view, account_info


app_name = 'auth'
urlpatterns = [
    path('', info, name='info'),
    path('auth/', login_or_register.as_view(), name='auth'),
    path('logout/', logout_view, name='logout'),
    path('@<str:account_username>/', account_info, name='account'),
]
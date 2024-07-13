from django.contrib import admin
from django.urls import path, include

from .views import login_or_register, info, logout_view, account_info, edit, code


app_name = 'auth'
urlpatterns = [
    path('', info, name='info'),
    path('edit_profile', edit.as_view(), name='edit_profile'),
    path('code', code.as_view(), name='code'),
    path('auth/', login_or_register.as_view(), name='auth'),
    path('logout/', logout_view, name='logout'),
    path('@<str:account_username>/', account_info, name='account'),
]
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from asgiref.sync import sync_to_async

from django.conf import settings

from typing import *

import os


class ModelUtils:
    def filename(name: str) -> str:
        result_name = name
        count = 0

        while os.path.exists(result_name):
            filename, ext = '.'.join(result_name.split('.')[:-1]), result_name.split('.')[-1]

            if len(filename.split('_')):
                if filename.split('_')[-1].isdigit():
                    count = int(filename.split('_')[-1])+1
                    filename = '_'.join(filename.split('_')[:-1])
            
            result_name = f'{filename}_{count}.{ext}'
        
        return result_name
    
    def avatar_filename(instance, filename: str) -> str:
        return ModelUtils.filename(f'{settings.AVATARS_URL}{filename}')


class User(AbstractUser):
    username = models.CharField(max_length=settings.MAX_USERNAME_LENGTH, unique=True)
    email = models.EmailField(unique=True, verbose_name='email')
    avatar = models.ImageField(upload_to=ModelUtils.avatar_filename, default=settings.DEFAULT_AVATAR_URL, verbose_name='Avatar Picture')
    last_updated = models.DateTimeField(auto_now=True, verbose_name='Last Update')
    score = models.IntegerField(default=0, verbose_name='Score')

    def save(self, *args, **kwargs):
        if self.id:
            old_user = User.objects.get(pk=self.id)

            if self.avatar and old_user.avatar != self.avatar and old_user.avatar.name != settings.DEFAULT_AVATAR_URL:
                old_user.avatar.delete()

        super(User, self).save(*args, **kwargs)

    def set_score(self, new_score: int):
        self.score = new_score
        self.save()

    def add_score(self, new_score: int):
        self.score += new_score
        self.save()

    @property
    def level(self) -> str:
        if self.score < 1000:
            return 'Новичок'
        elif self.score < 1400:
            return 'Любитель'
        elif self.score < 1600:
            return 'Третий разряд'
        elif self.score < 1800:
            return 'Второй разряд'
        elif self.score < 2000:
            return 'Первый разряд'
        elif self.score < 2200:
            return 'Кандидат в мастера'
        elif self.score < 2400:
            return 'Национальный мастер'
        elif self.score < 2500:
            return 'Международный мастер'
        else:
            return 'Гроссмейстер'

    @property
    def games(self) -> List['Game']:
        white_games = self.white_player_games.all()
        black_games = self.black_player_games.all()
        return sorted(list(white_games) + list(black_games), key=lambda game: game.created_at)

    @property
    def games_count(self) -> int:
        return len(self.games)

    @property
    def winrate(self) -> float:
        if self.losses > 0 and self.wins > 0:
            return round(self.wins/self.losses*100, 1)
        elif self.losses <= 0 and self.wins > 0:
            return 100.0
        else:
            return .0

    @property
    def lost_games(self) -> List['Game']:
        return [ game for game in self.games if game.winner != self ]
    @property
    def win_games(self) -> List['Game']:
        return [ game for game in self.games if game.winner == self ]

    @property
    def losses(self) -> int:
        return len(self.lost_games)
    @property
    def wins(self) -> int:
        return len(self.win_games)

    @property
    def is_in_game(self) -> bool:
        return bool([ game for game in self.games if not game.ended ])
    @property
    def active_game(self) -> 'Game':
        if self.is_in_game:
            return self.games[-1]
    @property
    def available_game(self) -> 'Game':
        return self.get_active_game


class Message(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages', verbose_name='Author')
    content = models.CharField(null=True, max_length=300)
    date_sent = models.DateTimeField(auto_now=True, verbose_name='Creation Time')

    def serealize(self) -> dict:
        return {
            'author': self.author.username,
            'author_avatar': self.author.avatar.url,
            'content': self.content,
            'date_sent': str(self.date_sent.strftime("%d.%m.%Y, %H:%M:%S")),
        }
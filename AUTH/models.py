from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from asgiref.sync import sync_to_async

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
        return ModelUtils.filename(f'avatars/{filename}')


class User(AbstractUser):
    email = models.EmailField(unique=True, verbose_name='email')
    avatar = models.ImageField(upload_to=ModelUtils.avatar_filename, default='avatars/default_user.png', verbose_name='Avatar Picture')
    last_updated = models.DateTimeField(auto_now=True, verbose_name='Last Update')
    global_score = models.IntegerField(default=0, verbose_name='Global Score')
    level = models.IntegerField(default=1, verbose_name='Level')

    def save(self, *args, **kwargs):
        if self.id:
            old_user = User.objects.get(pk=self.id)

            if self.avatar and old_user.avatar != self.avatar: # update avatar
                old_user.avatar.delete()

        super(User, self).save(*args, **kwargs)

    def set_score(self, new_score: int):
        self.global_score = new_score
        self.save()

    def add_score(self, new_score: int):
        self.global_score += new_score
        self.save()

    @property
    def games(self) -> List['Game']:
        white_games = self.white_player_games.all()
        black_games = self.black_player_games.all()
        return list(white_games) + list(black_games)

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
    def level(self) -> int:
        score_for_2_level = 10_000_000
        new_level_score = score_for_2_level
        level = 0
        score = self.global_score

        while score >= new_level_score:
            new_level_score = level*100 * score_for_2_level
            score -= new_level_score
            level += 1

        return level

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

    @sync_to_async
    def async_username(self) -> str:
        return self.username
    @sync_to_async
    def async_email(self) -> str:
        return self.email
    @sync_to_async
    def async_avatar(self) -> 'avatar':
        return self.avatar
    @sync_to_async
    def async_level(self) -> int:
        return self.level
    @sync_to_async
    def async_winrate(self) -> float:
        return self.winrate
    @sync_to_async
    def async_games_count(self) -> int:
        return self.games_count
    @sync_to_async
    def async_games(self) -> List['Game']:
        return self.games
    @sync_to_async
    def async_wins(self) -> List['Game']:
        return self.wins
    @sync_to_async
    def async_losses(self) -> List['Game']:
        return self.losses
    @sync_to_async
    def async_score(self) -> int:
        return self.global_score
from typing import *
from django.apps import AppConfig
from django.core.cache import cache
from asgiref.sync import sync_to_async
from django.conf import settings
from PIL import Image
from shutil import rmtree

import asyncio
import threading
import json
import random
import os, sys
# import signal

# shutdown_handlers = []


class GameConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'game'
    queue_consumers = []

    async def game_starter(self):
        from AUTH.models import User

        while True:
            from chess.consumers import queue_consumers
            self.queue_consumers = queue_consumers

            for con1 in self.queue_consumers:
                for con2 in self.queue_consumers:
                    if con1.user != con2.user and await self.similar_players(con1.user, con2.user):
                        intersection = list( list(set( range(con1.min, con1.max) ) & set( range(con2.min, con2.max) )) )

                        if len(intersection) > 0 and not con1.user in con2.black_list and not con2.user in con1.black_list:
                            if con1.searching and con2.searching:
                                con1.searching, con2.searching = False, False
                                con1.opponent, con2.opponent = con2, con1
                                await self.notice_queue_players(con1, con2)
                            elif (con1.clicked and not con1.ready) or (con2.clicked and not con2.ready):
                                await con1.cancel(ban=con2.user)
                                await con2.cancel(ban=con1.user)
                            elif con1.clicked and con1.ready and con2.clicked and con2.ready:
                                await self.start_game(*random.choice([[con1, con2], [con2, con1]]), await self.get_mid_time(con1, con2))

            await asyncio.sleep(1)

    async def start_game(self, white: 'QueueConsumer', black: 'QueueConsumer', time: int):
        from .models import Game
        game = await sync_to_async(Game.objects.create)(white_player=white.user, black_player=black.user, max_time=time * 60)
        await sync_to_async(game.save)()

        for con in [white, black]:
            if con in self.queue_consumers:
                await con.send(text_data=json.dumps({
                    'type': 'game_info',
                    'game_id': game.id,
                }))
                await con.disconnect(0)

    async def similar_players(self, user1: 'User', user2: 'User') -> bool:
        # it means values in (user.value - interval -> user.value + interval)
        level_interval = 2
        winrate_interval = 5
        games_interval = 10

        user1_winrate = await sync_to_async(lambda: user1.winrate)()
        user1_level = await sync_to_async(lambda: user1.winrate)()
        user1_games_count = await sync_to_async(lambda: user1.winrate)()

        user2_winrate = await sync_to_async(lambda: user2.winrate)()
        user2_level = await sync_to_async(lambda: user2.winrate)()
        user2_games_count = await sync_to_async(lambda: user2.winrate)()

        if user1_level - level_interval <= user2_level <= user1_level + level_interval:
            if user1_winrate - winrate_interval <= user2_winrate <= user1_winrate + winrate_interval:
                if user1_games_count - games_interval <= user2_games_count <= user1_games_count + games_interval:
                    return True

        return False

    async def get_mid_time(self, con1: 'QueueConsumer', con2: 'QueueConsumer') -> int:
        intersection = list( list(set( range(con1.min, con1.max) ) & set( range(con2.min, con2.max) )) )
        if len(intersection) > 0:
            return sum(intersection)//len(intersection)

    async def notice_queue_players(self, con1: 'QueueConsumer', con2: 'QueueConsumer'):
        await con1.send(text_data=json.dumps({
            'type': 'game_found',
            'max_time': await self.get_mid_time(con1, con2),
            'opponent': {
                'name': await sync_to_async(lambda: con2.user.username)(),
                'winrate': await sync_to_async(lambda: con2.user.winrate)(),
                'level': await sync_to_async(lambda: con2.user.level)(),
                'score': await sync_to_async(lambda: con2.user.global_score)(),
                'avatar': (await sync_to_async(lambda: con2.user.avatar)()).url
            }
        }))
        await con2.send(text_data=json.dumps({
            'type': 'game_found',
            'max_time': await self.get_mid_time(con1, con2),
            'opponent': {
                'name': await sync_to_async(lambda: con1.user.username)(),
                'winrate': await sync_to_async(lambda: con1.user.winrate)(),
                'level': await sync_to_async(lambda: con1.user.level)(),
                'score': await sync_to_async(lambda: con1.user.global_score)(),
                'avatar': (await sync_to_async(lambda: con1.user.avatar)()).url
            }
        }))

    # def resize_pieces_images(self, size: List[int], result_dir: str):
    #     global shutdown_handlers

    #     if os.path.isdir(result_dir):
    #         rmtree(result_dir)
    #     os.mkdir(result_dir)
    #     shutdown_handlers.append(lambda: rmtree(result_dir) if os.path.isdir(result_dir) else ...)

    #     for obj in os.listdir(settings.PIECES_DIR):
    #         if obj.split('.')[-1] == 'png' and obj.split('_')[0] in ['white', 'black']:
    #             image = Image.open(settings.PIECES_DIR + obj)
    #             image.save(result_dir + obj, sizes=[size])

    # def create_icons(self, size: List[int], result_dir: str):
    #     global shutdown_handlers

    #     if os.path.isdir(result_dir):
    #         rmtree(result_dir)
    #     os.mkdir(result_dir)
    #     shutdown_handlers.append(lambda: rmtree(result_dir) if os.path.isdir(result_dir) else ...)

    #     for obj in os.listdir(settings.MODIFIED_PIECES_DIR):
    #         if obj.split('.')[-1] == 'png':
    #             image = Image.open(settings.MODIFIED_PIECES_DIR + obj)
    #             image.save(result_dir + '.'.join(obj.split('.')[:-1]) + '.ico', format='ICO', sizes=[size])

    # def shutdown(self, signum, frame):
    #     global shutdown_handlers

    #     for func in shutdown_handlers:
    #         func()

    #     sys.exit(0)

    def ready(self):
        def start_game_starter_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.game_starter())

        thread = threading.Thread(target=start_game_starter_loop, daemon=True)
        thread.start()

        # self.resize_pieces_images(settings.PIECES_IMAGES_SIZE, settings.MODIFIED_PIECES_DIR)
        # self.create_icons(settings.ICONS_SIZE, settings.ICONS_DIR)

        # signal.signal(signal.SIGINT, self.shutdown)
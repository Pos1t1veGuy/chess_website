from django.apps import AppConfig
from django.core.cache import cache
from asgiref.sync import sync_to_async

import asyncio, threading, json, random


class GameConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'game'

    async def game_starter(self):
        from .models import Game

        while True:
            from chess.consumers import queue_consumers

            starter_queue = cache.get('starter_queue', [])

            for data in starter_queue:
                try:
                    user1, user2, max_time = data
                    if not (isinstance(user1, User) and isinstance(user2, User) and isinstance(max_time, (float, int))):
                        if max_time > 0:
                            print(f'error at game_starter: Invalid data in cache "starter_queue" {data}')
                            break
                except ValueError:
                    print(f'error at game_starter: Invalid data in cache "starter_queue" {data}')
                    break

                players = random.choice([[user1, user2], [user2, user1]])
                game = await sync_to_async(Game.objects.create)(white_player=players[0], black_player=players[1], max_time=max_time)
                game.save()

                print('accepted')
                for user in players:
                    if user in queue_consumers.keys():
                        user_consumer = queue_consumers.get(user)
                        await user_consumer.send(text_data=json.dumps({
                            'type': 'game_info',
                            'game_id': game.id,
                        }))
                        await user_consumer.close()

            await asyncio.sleep(1)

    def ready(self):
        from AUTH.models import User
        from .models import Game

        def start_game_starter_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.game_starter())

        thread = threading.Thread(target=start_game_starter_loop, daemon=True)
        thread.start()

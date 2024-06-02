from django.apps import AppConfig
from django.core.cache import cache
from asgiref.sync import sync_to_async

import asyncio, threading, json, random


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
                    if con1.user != con2.user and self.similar_players(con1.user, con2.user):
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
        #game = await sync_to_async(Game.objects.create)(white_player=white.user, black_player=black.user, max_time=time)
        #await sync_to_async(game.save)()

        print('accepted')
        for con in [white, black]:
            if con in self.queue_consumers:
                await con.send(text_data=json.dumps({
                    'type': 'game_info',
                    'game_id': 0#game.id,
                }))
                await con.disconnect()
                self.queue_consumers.remove(con)

    async def similar_players(self, user1: 'User', user2: 'User') -> bool:
        # it means values in (user.value - interval -> user.value + interval)
        level_interval = 2
        winrate_interval = 5
        games_interval = 10

        if await user1.async_level() - level_interval <= await user2.async_level() <= await self.user.async_level() + level_interval:
            if await user1.async_winrate() - winrate_interval <= await user2.async_winrate() <= await user1.async_winrate()+winrate_interval:
                if await user1.async_games_count() - games_interval <= await user2.async_games_count() <= await user1.async_games_count() + games_interval:
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
                'name': await con2.user.async_username(),
                'winrate': await con2.user.async_winrate(),
                'level': await con2.user.async_level(),
                'score': await con2.user.async_score(),
                'avatar': (await con2.user.async_avatar()).url
            }
        }))
        await con2.send(text_data=json.dumps({
            'type': 'game_found',
            'max_time': await self.get_mid_time(con1, con2),
            'opponent': {
                'name': await con1.user.async_username(),
                'winrate': await con1.user.async_winrate(),
                'level': await con1.user.async_level(),
                'score': await con1.user.async_score(),
                'avatar': (await con1.user.async_avatar()).url
            }
        }))

    def ready(self):
        def start_game_starter_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.game_starter())

        thread = threading.Thread(target=start_game_starter_loop, daemon=True)
        thread.start()

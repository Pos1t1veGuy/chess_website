from django.apps import AppConfig
from django.core.cache import cache
import asyncio as asio


class GameConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'game'

    async def game_starter(self):
        while 1:
            starter_queue = cache.get('starter_queue', [])

            for data in starter_queue:
                user1, user2, max_time = data
                players = random.choise([ [user1, user2], [user2, user1] ])
                game = Game(white_player=players[0], black_player=players[1], max_time=max_time)
                game.start()

                for user in players:
                    if user in queue_consumers.keys():
                        user_consumer = queue_consumers.get(user)
                        await user_consumer.send(text_data=json.dumps({
                            'type': 'game_info',
                            'game_id': game.id,
                        }))

            await asio.sleep(1)

    def ready(self):
        loop = asio.new_event_loop()
        asio.set_event_loop(loop)
        loop.run_until_complete(self.game_starter())

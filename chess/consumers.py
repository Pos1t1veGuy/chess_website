import json, random, asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache
from asgiref.sync import sync_to_async

from AUTH.models import User
from game.models import Game


queue_consumers = {}


class QueueConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        await self.accept()
        if self.user.is_authenticated:
            if not self.user.id in cache.get('queue', []):
                await self.add_to_queue()

                self.game_info = []
                self.searching = False
                self.ready_to_play = False
                self.clicked = False
                self.opponent = None
                self.max_time = None

                self.matchmaking_task = asyncio.create_task(self.matchmaking())

            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'info': 'account already in queue'
                }))
                await self.close()
        else:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'info': 'only registered users can play'
            }))
            await self.close()
    
    async def disconnect(self, close_code):
        await self.remove_from_queue()
        if hasattr(self, 'matchmaking_task'):
            self.matchmaking_task.cancel()
            try:
                await self.matchmaking_task
            except asyncio.CancelledError:
                pass

    async def receive(self, text_data):
        data = json.loads(text_data)
        mtype = data['type']
        
        match mtype:
            case 'time_form':
                if 'min' in data.keys() and 'max' in data.keys():
                    if data['min'].isdigit() and data['max'].isdigit():
                        tmin, tmax = int(data['min']), int(data['max'])
                        if 0 < tmin <= 60 and 0 < tmax <= 60 and tmin < tmax:
                            self.min, self.max = tmin, tmax
                            await self.add_time_queue(self.min, self.max)

            case 'i_am_ready':
                if await self.game_found():
                    if 'agreed' in data.keys():
                        if data['agreed'] == True:
                            self.ready_to_play = True
                            self.clicked = True

                            await (await self.opponent_consumer()).send(text_data=json.dumps({
                                'type': 'opponent_is_ready'
                            }))

            case 'cancel_game':
                if await self.game_found():
                    print('cancel2')
                    self.clicked = True
                    await (await self.opponent_consumer()).send(text_data=json.dumps({
                        'type': 'game_is_canceled'
                    }))
                    await self.send(text_data=json.dumps({
                        'type': 'game_is_canceled'
                    }))
                    await self.cancel()


    async def add_to_queue(self):
        queue = cache.get('queue', [])

        if self.user.is_authenticated:
            queue.append(self.user.id)
            queue_consumers[self.user.id] = self

            cache.set('queue', queue)
        else:
            raise Exception('User is not authenticated')

    async def remove_from_queue(self):
        queue = cache.get('queue', [])
        if self.user.is_authenticated:
            if self.user.id in queue:
                queue.remove(self.user.id)
            if self.user.id in queue_consumers:
                queue_consumers.pop(self.user.id)

            cache.set('queue', queue)
        else:
            raise Exception('User is not authenticated')

    async def add_time_queue(self, num1: int, num2: int):
        queue = cache.get('queue_times', {})
        if self.user.is_authenticated:
            queue[self.user.id] = [min(num1, num2), max(num1, num2)]
            cache.set('queue_times', queue)
        else:
            raise Exception('User is not authenticated')

    async def matchmaking(self):
        # it means values in (user.value - interval -> user.value + interval)
        level_interval = 2
        winrate_interval = 5
        games_interval = 10

        self.searching = True

        if not (hasattr(self, 'min') and hasattr(self, 'max')):
            self.min, self.max = 1, 60

        while 1:
            if self.opponent:
                print(3)
                if self.clicked and (await self.opponent_consumer()).clicked:
                    print(4)
                    if self.ready_to_play and (await self.opponent_consumer()).ready_to_play:
                        print(5)
                        starter_queue = cache.get('starter_queue', [])
                        if not [self.opponent.id, self.user.id, self.max_time] in starter_queue:
                            starter_queue.append([self.user.id, self.opponent.id, self.max_time])
                            cache.set('queue_times', starter_queue)
                    else:
                        print('cancel1')
                        await self.cancel()

            elif self.searching:
                queue = cache.get('queue', [])
                queue_times = cache.get('queue_times', {})

                for user_id in queue:
                    if user_id != self.user.id:
                        if user_id in queue_times.keys():
                            usermin, usermax = queue_times[user_id]
                        else:
                            usermin, usermax = 1, 60

                        user = await sync_to_async(User.objects.get)(id=user_id)

                        if await self.user.async_level() - level_interval <= await user.async_level() <= await self.user.async_level() + level_interval:
                            if await self.user.async_winrate()-winrate_interval <= await user.async_winrate() <= await self.user.async_winrate()+winrate_interval:
                                if await self.user.async_games_count()-games_interval <= await user.async_games_count() <= await self.user.async_games_count()+games_interval:
                                    intersection = list( list(set( range(usermin, usermax) ) & set( range(self.min, self.max) )) )
                                    if len(intersection) > 0 and self.searching:
                                        self.opponent = user
                                        if (await self.opponent_consumer()).searching:
                                            (await self.opponent_consumer()).searching = False
                                            self.searching = False

                                            self.max_time = sum(intersection)//len(intersection)
                                            await self.notice_players()

                        self.searching = True

            await self.send(text_data=json.dumps({
                'type': 'queue_players_info',
                'count': len(queue_consumers),
                'winrate': sum([ await (await sync_to_async(User.objects.get)(id=user_id)).async_winrate() for user_id in queue ])/len(queue),
                'level': sum([ await (await sync_to_async(User.objects.get)(id=user_id)).async_level() for user_id in queue ])/len(queue),
                'score': sum([ await (await sync_to_async(User.objects.get)(id=user_id)).async_score() for user_id in queue ])/len(queue),
                'games': sum([ await (await sync_to_async(User.objects.get)(id=user_id)).async_games_count() for user_id in queue ])/len(queue)
            }))
            await asyncio.sleep(1)

    async def opponent_consumer(self) -> 'QueueConsumer':
        if self.opponent:
            if self.opponent.id in queue_consumers.keys():
                print(1)
                opponent_consumer = queue_consumers.get(self.opponent.id)
                print(2)
                return opponent_consumer if isinstance(opponent_consumer, QueueConsumer) else None
    async def game_found(self) -> bool:
        return ( not self.searching and not (await self.opponent_consumer()).searching ) if self.opponent else False

    async def cancel(self):
        self.game_info = []
        self.searching = False
        self.ready_to_play = False
        self.clicked = False
        self.opponent = None
        self.max_time = None

    async def notice_players(self):
        opponent_consumer = await self.opponent_consumer()
        if opponent_consumer:
            if await self.game_found():
                if opponent_consumer.opponent == None:
                    opponent_consumer.opponent = self.user
                    print(4)
                    try:
                        await opponent_consumer.send(text_data=json.dumps({
                            'type': 'game_found',
                            'max_time': self.max_time,
                            'opponent': {
                                'name': await self.user.async_username(),
                                'winrate': await self.user.async_winrate(),
                                'level': await self.user.async_level(),
                                'score': await self.user.async_score(),
                                'avatar': (await self.user.async_avatar()).url
                            }
                        }))
                    except Exception as e:
                        print("Error sending data:", e)

                    print(4.5)

                    await self.send(text_data=json.dumps({
                        'type': 'game_found',
                        'max_time': self.max_time,
                        'opponent': {
                            'name': await self.opponent.async_username(),
                            'winrate': await self.opponent.async_winrate(),
                            'level': await self.opponent.async_level(),
                            'score': await self.opponent.async_score(),
                            'avatar': (await self.opponent.async_avatar()).url
                        }
                    }))
                    print(5)
                else:
                    await self.cancel()
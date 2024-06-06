import json, random, asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache
from asgiref.sync import sync_to_async

from AUTH.models import User
from game.models import Game


queue_consumers = []


class QueueConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        global queue_consumers

        self.user = self.scope['user']
        await self.accept()

        if self.user.is_authenticated:
            if not await sync_to_async(lambda: self.user.is_in_game)():
                if not self.user in queue_consumers:
                    await self.add_to_queue()

                    self.searching = True
                    self.ready = False
                    self.clicked = False
                    self.opponent = None
                    self.end = False
                    self.black_list = []

                    self.min, self.max = 1, 60

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
                    'info': 'user already in a game'
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
        self.end = True
        self.close()

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

            case 'i_am_ready':
                self.ready = True
                self.clicked = True
                await self.opponent.send(text_data=json.dumps({ 'type': 'opponent_is_ready' }))

            case 'cancel_game':
                self.clicked = True
                await self.opponent.send(text_data=json.dumps({ 'type': 'game_is_canceled' }))
                await self.send(text_data=json.dumps({ 'type': 'game_is_canceled' }))
                await self.cancel(ban=self.opponent.user)

    async def add_to_queue(self):
        global queue_consumers
        
        if self.user.is_authenticated:
            if not self.user in [ con.user for con in queue_consumers ]:
                queue_consumers.append(self)
            else:
                raise Exception('User already is in a queue')
        else:
            raise Exception('User is not authenticated')

    async def remove_from_queue(self):
        global queue_consumers
        
        if self.user.is_authenticated:
            if self in queue_consumers:
                queue_consumers.remove(self)
        else:
            raise Exception('User is not authenticated')

    async def matchmaking(self):
        global queue_consumers
        
        while 1:
            if self.end:
                break
                
            try:
                await self.send(text_data=json.dumps({
                    'type': 'queue_players_info',
                    'count': len(queue_consumers),
                    'winrate': sum([ await sync_to_async(lambda: con.user.winrate)() for con in queue_consumers ])/len(queue_consumers),
                    'level': sum([ await sync_to_async(lambda: con.user.level)() for con in queue_consumers ])/len(queue_consumers),
                    'score': sum([ await sync_to_async(lambda: con.user.global_score)() for con in queue_consumers ])/len(queue_consumers),
                    'games': sum([ await sync_to_async(lambda: con.user.games_count)() for con in queue_consumers ])/len(queue_consumers)
                }))
            except ZeroDivisionError:
                ...

            await asyncio.sleep(1)

    async def cancel(self, ban: 'User' = None):
        self.searching = True
        self.ready = False
        self.clicked = False
        self.opponent = None

        if isinstance(ban, User):
            self.black_list.append(ban)
        elif isinstance(self.opponent, User):
            self.black_list.append(self.opponent)

    def __str__(self):
        return f'Queue[{self.user.username}, accepted={self.ready}, clicked={self.clicked}]'
    def __repr__(self):
        return str(self)


class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        await self.accept()

        if self.user.is_authenticated:
            white = await sync_to_async(Game.objects.filter)(white_player=self.user, ended=False)
            black = await sync_to_async(Game.objects.filter)(black_player=self.user, ended=False)
            if list(white)+list(black):
                self.game = (list(white)+list(black))[0]
                self.end = False

                await self.send(text_data=json.dumps({
                    'type': 'pieces_info',
                    'board': self.game.movements[-1]
                }))
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'info': 'user has not a game'
                }))
                await self.close()
        else:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'info': 'only registered users can play'
            }))
            await self.close()
    
    async def disconnect(self, close_code):
        await self.remove_from_list()
        self.end = True
        self.close()

    async def receive(self, text_data):
        data = json.loads(text_data)
        mtype = data['type']
        
        match mtype:
            case 'user_gave_up':
                await self.gave_up()

    async def give_up(self):
        ...

    def __str__(self):
        return f'Game[{self.user.username}]'
    def __repr__(self):
        return str(self)
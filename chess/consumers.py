import json, random, asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache
from asgiref.sync import sync_to_async

from AUTH.models import User
from game.models import Game
from game.pieces import string_pieces
import traceback


queue_consumers = []
game_consumers_msgs = {}
players_in_game = [] 

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

class QueueConsumer1(AsyncWebsocketConsumer):
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
        print(f'Disconnect called with close_code: {close_code}')
        print(''.join(traceback.format_stack()))
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
        global players_in_game

        self.user = self.scope['user']
        players_in_game.append(self.user)
        await self.accept()

        if self.user.is_authenticated:
            white = await sync_to_async(Game.objects.filter)(white_player=self.user, ended=False)
            black = await sync_to_async(Game.objects.filter)(black_player=self.user, ended=False)
            if await sync_to_async(list)(white) + await sync_to_async(list)(black):
                self.game = (await sync_to_async(list)(white) + await sync_to_async(list)(black))[0]
                self.end = False

                self.color = await sync_to_async(self.game.get_color_by_user)(self.user)
                self.opponent = await sync_to_async(self.game.get_opponent_user)(self.user)

                await self.send_opponent({'type':'opponent_is_connected'})

                self.command_queue_task = asyncio.create_task(self.command_queue())
                self.client_comm_task = asyncio.create_task(self.client_comm())
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'info': 'user has not a game'
                }))
                await self.disconnect(0)
        else:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'info': 'only registered users can play'
            }))
            await self.disconnect(0)
    
    async def disconnect(self, close_code):
        global players_in_game
        if self.user in players_in_game:
            players_in_game.remove(self.user)
        self.end = True
        self.close()

    async def receive(self, text_data):
        data = json.loads(text_data)
        mtype = data['type']
        
        match mtype:
            case 'get_available_movements':
                if 'position' in data.keys():
                    if data['position']:
                        if len(data['position']) == 2 and all([ str(num).isdigit() for num in data['position'] ]):
                            pos = [ int(num) for num in data['position'] ]
                            if all([ 0 <= num <= 7 for num in pos ]):
                                piece = self.game[pos]
                                if piece:
                                    if piece.color == self.color:
                                        try:
                                            res = await sync_to_async(self.game.piece_movable_to)(pos)
                                        except Exception as e:
                                            res = {'type': str(e)}

                                        await self.send(text_data=json.dumps({
                                            'type': 'available_positions',
                                            'movements': res,
                                        }))
                                    else:
                                        await self.send(text_data=json.dumps({
                                            'type': f"You can not move { 'black' if self.color == 'white' else 'white' } pieces"
                                        }))
                                else:
                                    await self.send(text_data=json.dumps({'type': "Position is invalid"}))
                            else:
                                await self.send(text_data=json.dumps({'type': "Position is invalid"}))
                        else:
                            await self.send(text_data=json.dumps({'type': "Position is invalid"}))
                    else:
                        await self.send(text_data=json.dumps({'type': "Position is invalid"}))
            case 'user_gave_up':
                await self.game.give_up(self.game.get_color_by_user(self.user))
                await self.lose()
            case 'movement':
                if 'from' in data.keys() and 'to' in data.keys():
                    if data['from']:
                        if data['to']:
                            if len(data['from']) == 2 and all([ str(num).isdigit() for num in data['from'] ]):
                                piece = self.game[data['from']]
                                if piece:
                                    if piece.color == self.color:
                                        try:
                                            res = await sync_to_async(self.game.move)([ int(num) for num in data['from'] ], data['to'])
                                        except Exception as e:
                                            res = {'type': str(e)}
                                        await self.send(text_data=json.dumps(res))
                                    else:
                                        await self.send(text_data=json.dumps({
                                            'type': f"You can not move { 'black' if self.color == 'white' else 'white' } pieces"
                                        }))
                                else:
                                    await self.send(text_data=json.dumps({'type': "Position from is invalid"}))
                            else:
                                await self.send(text_data=json.dumps({'type': "Position from is invalid"}))
                        else:
                            await self.send(text_data=json.dumps({'type': "Position to is invalid"}))
                    else:
                        await self.send(text_data=json.dumps({'type': "Position from is invalid"}))

            case 'transform_pawn':
                if 'position' in data.keys() and 'to' in data.keys():
                    if data['position']:
                        if data['to']:
                            if len(data['position']) == 2 and all([ str(num).isdigit() for num in data['position'] ]):
                                piece = self.game[data['position']]
                                if piece:
                                    if piece.color == self.color:
                                        if data['to'] in string_pieces.lower():
                                            try:
                                                res = await sync_to_async(self.game.transform_pawn)(
                                                    [ int(num) for num in data['position'] ],
                                                    data['to'],
                                                    return_json=True
                                                )
                                            except Exception as e:
                                                res = {'type': str(e)}
                                            await self.send(text_data=json.dumps(res))
                                        else:
                                            await self.send(text_data=json.dumps({
                                                'type': "Typed invalid piece name in which the pawn will be transformed"
                                            }))
                                    else:
                                        await self.send(text_data=json.dumps({
                                            'type': f"You can not move { 'black' if self.color == 'white' else 'white' } pieces"
                                        }))
                                else:
                                    await self.send(text_data=json.dumps({'type': "Position is invalid"}))
                            else:
                                await self.send(text_data=json.dumps({'type': "Position is invalid"}))
                        else:
                            await self.send(text_data=json.dumps({'type': "Position to is invalid"}))
                    else:
                        await self.send(text_data=json.dumps({'type': "Position from is invalid"}))

            case 'castling':
                if 'direction' in data.keys():
                    if data['direction'] in ['left', 'right']:
                        try:
                            res = await sync_to_async(self.game.castling)(data['direction'], self.color)
                        except Exception as e:
                            res = {'type': str(e)}
                        await self.send(text_data=json.dumps(res))
                    else:
                        await self.send(text_data=json.dumps({
                            'type': "you typed invalid direction"
                        }))

    async def command_queue(self):
        global game_consumers_msgs
        
        while 1:
            if self.end:
                break
            
            if self.user in game_consumers_msgs.keys():
                for msg in game_consumers_msgs[self.user]:
                    await self.send(text_data=json.dumps(msg))
                    if msg['type'] == 'opponent_gived_up':
                        await self.win()
                    game_consumers_msgs[self.user].remove(msg)
            
            await asyncio.sleep(.5)

    async def client_comm(self):
        while 1:
            if self.end:
                break
            
            await self.send(text_data=json.dumps({
                'type': "game_info",
                'color': self.game.color,
                'board': self.game.movements[-1],
                'opponent_info': {
                    'is_connected': await self.is_opponent_alive(),
                    'time': self.game.passed_time('white' if self.color == 'black' else 'black'),
                    'score': await sync_to_async(lambda: (self.game.white_player_score if self.color == 'black' else self.game.black_player_score))(),
                },
                'self_info': {
                    'time': self.game.passed_time(self.color),
                    'score': await sync_to_async(lambda: (self.game.white_player_score if self.color == 'white' else self.game.black_player_score))(),
                }
            }))
            await asyncio.sleep(.5)

    async def send_opponent(self, data: dict):
        global game_consumers_msgs

        if self.opponent in game_consumers_msgs.keys():
            game_consumers_msgs[self.opponent].append(data)
        else:
            game_consumers_msgs[self.opponent] = [data]

    async def is_opponent_alive(self):
        global players_in_game
        return self.opponent in players_in_game

    async def lose(self):
        await self.send(text_data=json.dumps({
            'type': 'game_is_losed'
        }))
        await self.send_opponent({'type':'opponent_gived_up'})
        await self.disconnect(0)
    async def win(self):
        await self.send(text_data=json.dumps({
            'type': 'game_is_won'
        }))
        await self.disconnect(0)

    async def get_score(self):
        return await sync_to_async(lambda: self.score)()

    @property
    def score(self):
        if self.user == self.game.white_player:
            return self.game.white_player_score
        elif self.user == self.game.black_player:
            return self.game.black_player_score

    def __str__(self):
        return f'GameConsumer[{self.user.username}, color={self.color}, score={self.score}]'
    def __repr__(self):
        return str(self)
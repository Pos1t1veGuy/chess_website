import json, random, asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache
from asgiref.sync import sync_to_async
from django.urls import reverse

from AUTH.models import User
from game.models import Game
from game.pieces import string_pieces
import traceback
import functools


queue_consumers = []
game_consumers_msgs = {}
players_in_game = []
revengers = {}


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
        global players_in_game

        self.user = self.scope['user']
        players_in_game.append(self.user)
        await self.accept()

        if self.user.is_authenticated:
            try:
                game = (await sync_to_async(lambda: self.user.games)())[-1]
            except IndexError:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'info': 'user has not a game'
                }))
                await self.disconnect(0)

            if not game.ended:
                self.end = False

                self.game_id = game.id
                self.opponent = await sync_to_async(game.get_opponent_user)(self.user)
                self.color = await sync_to_async(game.get_color_by_user)(self.user)
                self.opponent_color = 'black' if self.color == 'white' else 'white'

                self.movement_count = game.movement_count

                await self.send_opponent({'type':'opponent_is_connected'})
                await self.send_available_movements(game)

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

        game = await sync_to_async(Game.objects.get)(id=self.game_id)
        if game.starting:
            self.give_up()
        else:
            await self.send_opponent({'type': 'opponent_is_disconnected'})

        self.close()

    async def receive(self, text_data):
        global revengers
        data = json.loads(text_data)
        mtype = data['type']
        
        game = await sync_to_async(Game.objects.get)(id=self.game_id)

        match mtype:
            case 'user_gave_up':
                if not game.ended:
                    await self.give_up()
                else:
                    await self.send(text_data=json.dumps({
                        'type': "redirect",
                        'url': reverse('chess:home')
                    }))
            case 'movement':
                if not game.ended:
                    if 'from' in data.keys() and 'to' in data.keys():
                        if data['from']:
                            if data['to']:
                                if len(data['from']) == 2 and all([ str(num).isdigit() for num in data['from'] ]):
                                    piece = game[data['from']]
                                    if piece:
                                        if piece.color == self.color:
                                            try:
                                                res = await sync_to_async(game.move)([ int(num) for num in data['from'] ], data['to'])
                                                await self.send(text_data=json.dumps({'type': 'success'}))
                                            except Exception as e:
                                                await self.send(text_data=json.dumps({'type': str(e)}))
                                        else:
                                            await self.send(text_data=json.dumps({
                                                'type': f"You can not move {self.opponent_color} pieces"
                                            }))
                                    else:
                                        await self.send(text_data=json.dumps({'type': "Position from is invalid"}))
                                else:
                                    await self.send(text_data=json.dumps({'type': "Position from is invalid"}))
                            else:
                                await self.send(text_data=json.dumps({'type': "Position to is invalid"}))
                        else:
                            await self.send(text_data=json.dumps({'type': "Position from is invalid"}))
                else:
                    await self.send(text_data=json.dumps({
                        'type': "redirect",
                        'url': reverse('chess:home')
                    }))

            case 'transform_pawn':
                if not game.ended:
                    if 'position' in data.keys() and 'to' in data.keys():
                        if data['position']:
                            if data['to']:
                                if len(data['position']) == 2 and all([ str(num).isdigit() for num in data['position'] ]):
                                    piece = game[data['position']]
                                    if piece:
                                        if piece.color == self.color:
                                            if data['to'] in string_pieces.lower():
                                                try:
                                                    res = await sync_to_async(game.transform_pawn)(
                                                        [ int(num) for num in data['position'] ],
                                                        data['to'],
                                                        return_json=True
                                                    )
                                                    await self.send(text_data=json.dumps({'type': 'success'}))
                                                except Exception as e:
                                                    await self.send(text_data=json.dumps({'type': str(e)}))
                                            else:
                                                await self.send(text_data=json.dumps({
                                                    'type': "Typed invalid piece name in which the pawn will be transformed"
                                                }))
                                        else:
                                            await self.send(text_data=json.dumps({
                                                'type': f"You can not move {self.opponent_color} pieces"
                                            }))
                                    else:
                                        await self.send(text_data=json.dumps({'type': "Position is invalid"}))
                                else:
                                    await self.send(text_data=json.dumps({'type': "Position is invalid"}))
                            else:
                                await self.send(text_data=json.dumps({'type': "Position to is invalid"}))
                        else:
                            await self.send(text_data=json.dumps({'type': "Position from is invalid"}))
                else:
                    await self.send(text_data=json.dumps({
                        'type': "redirect",
                        'url': reverse('chess:home')
                    }))

            case 'castling':
                if not game.ended:
                    if 'direction' in data.keys():
                        if data['direction'] in ['left', 'right']:
                            try:
                                res = await sync_to_async(game.castling)(data['direction'], self.color)
                                await self.send(text_data=json.dumps({'type': 'success'}))
                            except Exception as e:
                                await self.send(text_data=json.dumps({'type': str(e)}))
                        else:
                            await self.send(text_data=json.dumps({
                                'type': "you typed invalid direction"
                            }))
                else:
                    await self.send(text_data=json.dumps({
                        'type': "redirect",
                        'url': reverse('chess:home')
                    }))

            case 'want_to_revenge':
                await self.send_opponent({'type': 'opponent_want_to_revenge'})
                if game in revengers.keys():
                    revengers[game].append(self)
                else:
                    revengers[game] = [self]

    async def command_queue(self):
        global game_consumers_msgs

        while 1:
            game = await sync_to_async(Game.objects.get)(id=self.game_id)
            if self.user in game_consumers_msgs.keys():
                for msg in game_consumers_msgs[self.user]:
                    await self.send(text_data=json.dumps(msg))
                    game_consumers_msgs[self.user].remove(msg)
            
            await asyncio.sleep(.8)

            if self.end:
                break

    async def client_comm(self):
        while 1:
            game = await sync_to_async(Game.objects.get)(id=self.game_id)
            
            if not game.ended:
                self_check = False
                opponent_check = False
                kings = await sync_to_async(lambda: game.kings)()
                if any([ king.checkmate for king in kings ]):
                    king = [ king for king in kings if king.checkmate ][0]
                    if king.color == self.color:
                        await self.lose()
                    else:
                        await self.win()
                elif any([ king.mate for king in kings ]):
                    await self.stalemate()
                elif any([ king.check for king in kings ]):
                    self_check = self.color in [ king.color for king in kings if king.check ]
                    opponent_check = self.opponent_color in [ king.color for king in kings if king.check ]

                movement_count = await sync_to_async(lambda: game.movement_count)()
                if self.movement_count < movement_count:
                    self.movement_count = movement_count
                    await self.send_available_movements(game)

                await self.send(text_data=json.dumps({
                    'type': "game_info",
                    'color': game.color,
                    'board': game.movements[-1],
                    'opponent_info': {
                        'is_connected': await self.is_opponent_alive(),
                        'time': await sync_to_async(game.passed_time)(self.opponent_color),
                        'score': await sync_to_async(lambda: (game.white_player_score if self.color == 'black' else game.black_player_score))(),
                        'check': opponent_check,
                    },
                    'self_info': {
                        'time': await sync_to_async(game.passed_time)(self.color),
                        'score': await sync_to_async(lambda: (game.white_player_score if self.color == 'white' else game.black_player_score))(),
                        'check': self_check,
                    }
                }))
            else:
                break

            if self.end:
                break

            await asyncio.sleep(.25)

    async def send_opponent(self, data: dict):
        global game_consumers_msgs

        try:
            if self.opponent in game_consumers_msgs.keys():
                game_consumers_msgs[self.opponent] = [ *game_consumers_msgs[self.opponent], data ]
            else:
                game_consumers_msgs[self.opponent] = [data]
        except AttributeError:
            self.disconnect(0)

    async def send_available_movements(self, game: 'Game'):
        movements = await sync_to_async(game.all_pieces_movements)(self.color, return_dict=True)
        await self.send(text_data=json.dumps({
            'type': "available_movements",
            'positions': list(movements.keys()),
            'movements': list(movements.values()),
        }))

    async def is_opponent_alive(self):
        global players_in_game
        return self.opponent in players_in_game

    async def lose(self, last_msg: bool = False):
        game = await sync_to_async(Game.objects.get)(id=self.game_id)
        lost_pieces = [
            await sync_to_async(lambda color: game.lost_pieces_by_color(color))(self.color),
            await sync_to_async(lambda color: game.lost_pieces_by_color(color))(self.opponent_color),
        ]
        await self.send(text_data=json.dumps({
            'type': 'end_info',
            'score': await self.get_score(),
            'time': await sync_to_async(game.passed_time)(self.color),
            'movement_count': await sync_to_async(lambda: game.movement_count)(),
            'lost_pieces': len(lost_pieces[0]),
            'opponent_lost_pieces': len(lost_pieces[1]),
            'lost_price': sum([ piece.price for piece in lost_pieces[0] ]),
            'opponent_lost_piece': sum([ piece.price for piece in lost_pieces[1] ]),
            'result': 'lose',
        }))
        if not last_msg:
            await self.send_opponent({
                'type': 'end_info',
                'score': await self.get_score(),
                'time': await sync_to_async(game.passed_time)(self.opponent_color),
                'movement_count': await sync_to_async(lambda: game.movement_count)(),
                'lost_pieces': len(lost_pieces[1]),
                'opponent_lost_pieces': len(lost_pieces[0]),
                'lost_price': sum([ piece.price for piece in lost_pieces[1] ]),
                'opponent_lost_piece': sum([ piece.price for piece in lost_pieces[0] ]),
                'result': 'win',
            })
        await self.disconnect(0)
    async def win(self, last_msg: bool = False):
        game = await sync_to_async(Game.objects.get)(id=self.game_id)
        lost_pieces = [
            await sync_to_async(lambda color: game.lost_pieces_by_color(color))(self.color),
            await sync_to_async(lambda color: game.lost_pieces_by_color(color))(self.opponent_color),
        ]
        await self.send(text_data=json.dumps({
            'type': 'end_info',
            'score': await self.get_score(),
            'time': await sync_to_async(game.passed_time)(self.color),
            'movement_count': await sync_to_async(lambda: game.movement_count)(),
            'lost_pieces': len(lost_pieces[0]),
            'opponent_lost_pieces': len(lost_pieces[1]),
            'lost_price': sum([ piece.price for piece in lost_pieces[0] ]),
            'opponent_lost_piece': sum([ piece.price for piece in lost_pieces[1] ]),
            'result': 'win',
        }))
        if not last_msg:
            await self.send_opponent({
                'type': 'end_info',
                'score': await self.get_score(),
                'time': await sync_to_async(game.passed_time)(self.opponent_color),
                'movement_count': await sync_to_async(lambda: game.movement_count)(),
                'lost_pieces': len(lost_pieces[1]),
                'opponent_lost_pieces': len(lost_pieces[0]),
                'lost_price': sum([ piece.price for piece in lost_pieces[1] ]),
                'opponent_lost_piece': sum([ piece.price for piece in lost_pieces[0] ]),
                'result': 'lose',
            })
        await self.disconnect(0)
    async def stalemate(self, last_msg: bool = False):
        game = await sync_to_async(Game.objects.get)(id=self.game_id)
        lost_pieces = [
            await sync_to_async(lambda color: game.lost_pieces_by_color(color))(self.color),
            await sync_to_async(lambda color: game.lost_pieces_by_color(color))(self.opponent_color),
        ]
        await self.send(text_data=json.dumps({
            'type': 'end_info',
            'score': await self.get_score(),
            'time': await sync_to_async(game.passed_time)(self.color),
            'movement_count': await sync_to_async(lambda: game.movement_count)(),
            'lost_pieces': len(lost_pieces[0]),
            'opponent_lost_pieces': len(lost_pieces[1]),
            'lost_price': sum([ piece.price for piece in lost_pieces[0] ]),
            'opponent_lost_piece': sum([ piece.price for piece in lost_pieces[1] ]),
            'result': 'stalemate',
        }))
        if not last_msg:
            await self.send_opponent({
                'type': 'end_info',
                'score': await self.get_score(),
                'time': await sync_to_async(game.passed_time)(self.opponent_color),
                'movement_count': await sync_to_async(lambda: game.movement_count)(),
                'lost_pieces': len(lost_pieces[1]),
                'opponent_lost_pieces': len(lost_pieces[0]),
                'lost_price': sum([ piece.price for piece in lost_pieces[1] ]),
                'opponent_lost_piece': sum([ piece.price for piece in lost_pieces[0] ]),
                'result': 'stalemate',
            })
        await self.disconnect(0)

    async def give_up(self):
        game = await sync_to_async(Game.objects.get)(id=self.game_id)
        if not game.playing:
            await sync_to_async(game.start)()
        await self.lose()
        await sync_to_async(game.give_up)(self.color)

    async def get_score(self) -> int:
        return await sync_to_async(lambda: self.score)()

    @property
    def score(self) -> int:
        game = Game.objects.get(id=self.game_id)
        if self.user == game.white_player:
            return game.white_player_score
        elif self.user == game.black_player:
            return game.black_player_score

    def __str__(self):
        return f'GameConsumer[{self.user.username}, color={self.color}, score={self.score}]'
    def __repr__(self):
        return str(self)
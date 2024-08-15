from django.db import models
from django.utils import timezone

from AUTH.models import User

from .pieces import *
from copy import deepcopy


def movements_to_str(soft_movements) -> list:
	res = []

	for movement in soft_movements:
		matrix = value_matrix('1', 8, 8)
		for y, line in enumerate(movement):
			for x, piece in enumerate(line):
				if piece:
					matrix[y][x] = str(piece)
				else:
					matrix[y][x] = ''

		res.append(matrix)

	return res

def str_to_movements(movements) -> list:
	res = []

	for movement in movements:
		matrix = value_matrix(None, 8, 8)
		for y, line in enumerate(movement):
			for x, piece in enumerate(line):
				parts = piece.split(' ')
				if len(parts) == 2:
					matrix[y][x] = str_to_piece(piece, pos=[x,y])
				else:
					matrix[y][x] = None

		res.append(matrix)

	return res

def str_to_piece(piece: str, pos=[0,0]) -> Piece:
	parts = piece.split(' ')
	if parts[0] in ['Pawn','Rook','Bishop','Knight','Queen','King'] and parts[1] in ['black','white']:
		return eval(f'{parts[0]}("{parts[1]}", pos={pos})')

def value_matrix(value, x: int, y: int) -> list:
	return [[value for _ in range(x)] for _ in range(y)]

def if_not_ended(func):
	def wrapper(self, *args, **kwargs):
		if self.ended:
			raise ValueError("The game is ended")
		return func(self, *args, **kwargs)
	return wrapper

def if_not_ended_and_started(func):
	def wrapper(self, *args, **kwargs):
		
		if self.ended:
			raise ValueError("The game is ended")
		if not self.playing:
			raise ValueError("The game is not started")

		return func(self, *args, **kwargs)
	return wrapper

def if_time_is_not_up(func):
	def wrapper(self, *args, **kwargs):

		if self.playing:
			timedelta = (timezone.now() - self.last_movement_time).total_seconds()
			if self.color == 'white' and self.white_player_time + timedelta >= self.max_time:
				self.end(win='black', res='time')
			elif self.color == 'black' and self.black_player_time + timedelta >= self.max_time:
				self.end(win='white', res='time')

		return func(self, *args, **kwargs)
	return wrapper


class Game(models.Model):
	start_time = models.DateTimeField(auto_now=True, verbose_name='Start Time')
	end_time = models.DateTimeField(null=True, blank=True, verbose_name='End Time')
	max_time = models.IntegerField(verbose_name='Maximum Time (seconds)', default=15 * 60)
	last_movement_time = models.DateTimeField(auto_now=True, verbose_name='Last Movement Time')
	created_at = models.DateTimeField(auto_now=True, verbose_name='Creation Time')

	white_player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='white_player_games', verbose_name='White Player')
	black_player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='black_player_games', verbose_name='Black Player')
	winner = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='winner', verbose_name='Winner')

	white_player_time = models.IntegerField(default=0, verbose_name='White PLayer Time (seconds)')
	black_player_time = models.IntegerField(default=0, verbose_name='White PLayer Time (seconds)')

	white_player_score = models.IntegerField(default=0, verbose_name='White PLayer Score')
	black_player_score = models.IntegerField(default=0, verbose_name='White PLayer Score')

	destroyed_pieces = models.JSONField(default=list, verbose_name='Destroyed Pieces')

	movements = models.JSONField(default=movements_to_str([[
		[
			Rook('black', pos=[0,0]), Knight('black', pos=[1,0]), Bishop('black', pos=[2,0]), Queen('black', pos=[3,0]),
			King('black', pos=[4,0]), Bishop('black', pos=[5,0]), Knight('black', pos=[6,0]), Rook('black', pos=[7,0])
		],
		[Pawn('black', pos=[i, 1]) for i in range(8)],
		[None] * 8,
		[None] * 8,
		[None] * 8,
		[None] * 8,
		[Pawn('white', pos=[i, 6]) for i in range(8)],
		[
			Rook('white', pos=[0,7]), Knight('white', pos=[1,7]), Bishop('white', pos=[2,7]), Queen('white', pos=[3,7]),
			King('white', pos=[4,7]), Bishop('white', pos=[5,7]), Knight('white', pos=[6,7]), Rook('white', pos=[7,7])
		],
	]]), verbose_name='movements')
	playing = models.BooleanField(default=False)
	ended = models.BooleanField(default=False)
	end_reason = models.CharField(null=True, max_length=50)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.actions = [self.move, self.castling, self.transform_pawn]

	@if_time_is_not_up
	def move(self, _from: list, _to: list, predict_score: bool = False, start_score: int = 100):
		last_movement = self.soft_movements[-1]
		first_movement = False

		if isinstance(last_movement[_from[1]][_from[0]], Piece):
			if self.movement_count == 0 and last_movement[_from[1]][_from[0]].color == self.color == 'white':
				first_movement = True
			elif last_movement[_from[1]][_from[0]].color != self.color: # everything has its time
				raise ValueError(f"{len(self.movements)} movement is for {self.color}, but piece at {_from} is a {last_movement[_from[1]][_from[0]].color}")
		else:
			raise ValueError("Position from at last game move is empty or not on board, there must be piece to move it")

		save_king_movements = self.get_save_king_movements(self.color)
		if len(save_king_movements) == 0:
			self.end(win='black' if self.color == 'white' else 'white', res='checkmate')

		for i, fromto in enumerate([_from, _to]):
			if isinstance(fromto, list):
				if len(fromto) == 2:
					if isinstance(fromto[0], int) and isinstance(fromto[1], int):
						if 0 <= fromto[0] <= 7 and 0 <= fromto[1] <= 7:
							continue

			raise ValueError(f"Position {['from', 'to'][i]} is invalid: {fromto}")
		
		if self.ended:
			raise ValueError("The game is ended")
		if not self.playing and not first_movement:
			raise ValueError("The game is not started")

		destroyed_piece = last_movement[_to[1]][_to[0]] if isinstance(last_movement[_to[1]][_to[0]], Piece) else None

		new_movement = self.make_movement(last_movement, _from, _to, reg_destroyed_pieces=True)
		if (list(_from), list(_to)) in save_king_movements or not (tuple(_from), tuple(_to)) in all_movements:
			if first_movement:
				self.start()
			self.save_movement(new_movement)
		else:
			formatted_save_movements = '\n'.join([
				f'{i+1}. [{movement[0]} -> {movement[1]}]' for i, movement in enumerate(save_king_movements)
			])
			raise ValueError(f"Your king is in danger! You must safe king. To do it, you have this movements:\n{formatted_save_movements}")

	@if_time_is_not_up
	def transform_pawn(self, pos_or_pawn, to: Piece, predict_score: bool = False, start_score: int = 100):
		if isinstance(pos_or_pawn, (list, tuple)):
			if len(pos_or_pawn) == 2:
				if isinstance(self[pawn_pos], Pawn):
					obj = self[pawn_pos]
				else:
					raise ValueError(f'Not Pawn at position {pos_or_pawn}')
			else:
				raise ValueError(f'Invalid position {pos_or_pawn}. Position must be list/tuple with 2 integer values')

		if isinstance(pos_or_pawn, Pawn):
			if self[pos_or_pawn.pos] == Pawn:
				obj = pos_or_pawn
			else:
				raise ValueError(f'Argument {pos_or_pawn} with pos {pos_or_pawn.pos} is not in this game. It must be at last movement ( game.soft_movements[-1] to get it )')
		else:
			raise ValueError(f'Invalid argument {pos_or_pawn}. It must be position (list/tuple with 2 integer values) or Pawn object')

		if isinstance(to, Piece) and not isinstance(to, (Pawn, King)):
			last_movement = self.soft_movements[-1]
			if self.color == obj.color: # everything has its time
				if obj.color == 'white' and obj.pos[1] in [0, 1]:

					if self.ended:
						raise ValueError("The game is ended")
					if not self.playing:
						raise ValueError("The game is not started")

					last_movement[obj.x][0] = to(obj.color, pos=[obj.x][0])
					if len(self.get_save_king_movements(self.color)) == 0:
						self.end(win='black' if self.color == 'white' else 'white', res='checkmate')
					self.save_movement(last_movement)

				elif obj.color == 'black' and obj.pos[1] in [6, 7]:

					last_movement[obj.x][7] = to(obj.color, pos=[obj.x][7])
					self.save_movement(last_movement)

				else:
					raise ValueError(f'{str(obj)} at {obj.pos} can not be transformated')
			else:
				raise ValueError(f"{len(self.movements)} movement is for {self.color}, but this Pawn is a {obj.color}")
		else:
			raise ValueError(f'Invalid argument {to}. It must be Piece object ( not Pawn )')

	@if_not_ended_and_started
	@if_time_is_not_up
	def give_up(self, color: str, return_json: bool = False):
		self.end(win=color, res='gived_up')

	@if_not_ended
	@if_time_is_not_up
	def castling(self, color: str, side: str, predict_score: bool = False, start_score: int = 100):
		if side in ['left', 'right']: # 1 - left, 0 - right
			side = 1 if side == 'left' else 0
			side = not side if self.color == 'black' else side
		else:
			raise ValueError(f'Invalid argument {side}. It must be "left"/"right" ( if it is for black player it will be mirrored )')

		if color == self.color: # everything has its time
			if self.ended:
				raise ValueError("The game is ended")
			if not self.playing:
				raise ValueError("The game is not started")

			kings = [ piece for piece in self.alive_pieces if isinstance(piece, King) ]
			king = [ king for king in kings if king.color == color ][0]
			rooks = [ rook for rook in [ piece for piece in self.alive_pieces if isinstance(piece, Rook) ] if rook.color == color ]
			moveless_rooks = [ rook for rook in rooks if not rook.moved ]
			moveless_rooks_positions = [ rook.pos for rook in moveless_rooks ]

			enemy_positions = [ piece.pos for piece in (self.black_pieces if color == 'white' else self.white_pieces) ]
			enemy_movable_to = [
				piece.movable_to(
					enemies=self.black_pieces if piece.color == 'white' else self.white_pieces,
					friends=self.black_pieces if piece.color == 'black' else self.white_pieces
				) for piece in (self.black_pieces if color == 'white' else self.white_pieces)
			]
			friend_positions = [ piece.pos for piece in (self.black_pieces if color == 'black' else self.white_pieces) ]

			if moveless_rooks and not king.moved:
				new_movement = self.soft_movements[-1]
				if side == 1: # left for black ( mirrored ) and white
					if [0,7] in moveless_rooks_positions and color == 'white':
						if not [1,7] in friend_positions+enemy_positions and not [2,7] in friend_positions+enemy_positions and not [3,7] in friend_positions+enemy_positions:
							if not [2,7] in enemy_movable_to:
								new_movement = self.piece_set_pos(king.pos, [2,7], movement=new_movement)
								new_movement = self.piece_set_pos([0,7], [3,7], movement=new_movement)
					if [7,0] in moveless_rooks_positions and color == 'black':
						if not [5,0] in friend_positions+enemy_positions and not [6,0] in friend_positions+enemy_positions:
							if not [6,0] in enemy_movable_to:
								new_movement = self.piece_set_pos(king.pos, [6,0], movement=new_movement)
								new_movement = self.piece_set_pos([7,0], [5,0], movement=new_movement)
				else: # right for black ( mirrored ) and white
					if [7,7] in moveless_rooks_positions and color == 'white':
						if not [5,7] in friend_positions+enemy_positions and not [6,7] in friend_positions+enemy_positions:
							if not [6,7] in enemy_movable_to:
								new_movement = self.piece_set_pos(king.pos, [6,7], movement=new_movement)
								new_movement = self.piece_set_pos([7,7], [5,7], movement=new_movement)
					if [0,0] in moveless_rooks_positions and color == 'black':
						if not [0,1] in friend_positions+enemy_positions and not [0,2] in friend_positions+enemy_positions and not [0,3] in friend_positions+enemy_positions:
							if not [0,2] in enemy_movable_to:
								new_movement = self.piece_set_pos(king.pos, [0,2], movement=new_movement)
								new_movement = self.piece_set_pos([0,0], [3,0], movement=new_movement)

				if len(self.get_save_king_movements(self.color)) == 0:
					self.end(win='black' if self.color == 'white' else 'white', res='checkmate')
				self.save_movement(new_movement)

			else:
				raise ValueError(f"You can not make castling because you are already moved 2 rooks or 1 rook & king")
		else:
			raise ValueError(f"{len(self.movements)} movement is for {self.color}, but piece at {_from} is a {last_movement[_from[1]][_from[0]].color}")

	@if_not_ended
	@if_time_is_not_up
	def make_movement(self, last_movement: list, _from: list, _to: list, reg_destroyed_pieces: bool = False) -> list:
		# sets position to piece and will destroy enemy piece if it is at TO position and checks kings
		kings = [ piece for piece in self.alive_pieces if isinstance(piece, King) ]
		last_movement[_from[1]][_from[0]].move(_to,
			enemies=self.black_pieces if last_movement[_from[1]][_from[0]].color == 'white' else self.white_pieces,
			friends=self.black_pieces if last_movement[_from[1]][_from[0]].color == 'black' else self.white_pieces)

		if last_movement[_to[1]][_to[0]]: # if piece at TO position
			if last_movement[_to[1]][_to[0]] != self.color: # if it is an enemy piece
				if reg_destroyed_pieces:
					self.destroyed_pieces.append(str(last_movement[_to[1]][_to[0]]))

				last_movement[_to[1]][_to[0]].destroyed = True
				last_movement[_to[1]][_to[0]] = last_movement[_from[1]][_from[0]]

		last_movement[_to[1]][_to[0]] = last_movement[_from[1]][_from[0]]
		last_movement[_from[1]][_from[0]] = None
		kings = []
		for y, line in enumerate(last_movement):
			for x, piece in enumerate(line):
				if isinstance(piece, King):
					kings.append(piece)

		if len(kings) != 2 or not ('white' in [ king.color for king in kings ] and 'black' in [ king.color for king in kings ]):
			raise ValueError('Game must have 2 king for white and black players at board')

		return last_movement

	@if_not_ended
	@if_time_is_not_up
	def save_movement(self, new_movement: list):
		now = timezone.now()

		if self.movement_count > 0:
			timedelta = (now - self.last_movement_time).total_seconds()
			if self.color == 'white':
				self.white_player_time += timedelta
			else:
				self.black_player_time += timedelta
		self.last_movement_time = now

		movements = self.soft_movements
		movements.append(new_movement)
		self.movements = movements_to_str(movements)

		self.save()

	def get_save_king_movements(self, color: str) -> list:
		last_movement = self.soft_movements[-1]
		save_king_movements = []
		for __from, __to in self.all_pieces_movements(color):
			movement = self.make_movement(deepcopy(last_movement), __from, __to)
			next_king = [piece for piece in (self.black_pieces if color == 'black' else self.white_pieces) if isinstance(piece, King)][0]
			if not next_king.check:
				save_king_movements.append((list(__from), list(__to)))
		return save_king_movements

	@if_not_ended
	@if_time_is_not_up
	def piece_movable_to(self, piece: 'Piece'):
		if isinstance(piece, Piece):
			movable_to = piece.movable_to(
				enemies=self.black_pieces if piece.color == 'white' else self.white_pieces,
				friends=self.black_pieces if piece.color == 'black' else self.white_pieces
			)
		elif isinstance(piece, (list, tuple)):
			if len(piece) == 2 and all([ isinstance(num, int) for num in piece ]):
				if all([ 0 <= num <= 7 for num in piece ]):
					return self.piece_movable_to(self[piece])
				else:
					raise ValueError(f'piece_movable_to takes Piece object or list with board position, not {piece}')
			else:
				raise ValueError(f'piece_movable_to takes Piece object or list with board position, not {piece}')
		else:
			raise ValueError(f'piece_movable_to takes Piece object or list with board position, not {piece}')

		all_movements = self.all_pieces_movements(color=piece.color, return_dict=True)
		if tuple(piece.pos) in all_movements.keys():
			return list(tuple(set([ tuple(pos) for pos in movable_to ]) & set(all_movements[tuple(piece.pos)])))
		else:
			return []

	@if_not_ended
	@if_time_is_not_up
	def piece_set_pos(self, _from: list, _to: list, movement: list = None, save: bool = False):
		# sets position to piece and ignore any piece at TO position
		if isinstance(self[_from], Piece):
			if movement:
				last_movement = movement
			else:
				last_movement = self.soft_movements[-1]

			last_movement[_from[1]][_from[0]].set_pos(_to)
			last_movement[_to[1]][_to[0]] = last_movement[_from[1]][_from[0]]
			last_movement[_from[1]][_from[0]] = ''
			if save:
				self.save_movement(last_movement)
			else:
				return last_movement
		else:
			raise ValueError("Position '_from' at last game move is empty, there must be piece to move it")

	@if_not_ended
	@if_time_is_not_up
	def passed_time(self, color: str) -> int:
		if self.playing:
			if self.color == color:
				timedelta = (timezone.now() - self.last_movement_time).total_seconds()
				if color == 'white':
					return int(self.white_player_time + timedelta)
				else:
					return int(self.black_player_time + timedelta)
			else:
				if color == 'white':
					return int(self.white_player_time)
				else:
					return int(self.black_player_time)
		elif self.ended:
			if color == 'white':
				return int(self.white_player_time)
			else:
				return int(self.black_player_time)
		return 0

	@if_not_ended
	@if_time_is_not_up
	def time_left(self, color: str) -> int:
		return int(self.max_time - self.passed_time(color))

	@if_not_ended
	def start(self):
		self.last_movement_time = timezone.now()
		self.playing = True
		self.save()

	@if_not_ended
	@if_time_is_not_up
	def stop(self):
		self.last_movement_time = timezone.now()
		self.playing = False
		self.save()

	@if_not_ended
	def end(self, win: str = None, res: str = None):
		self.end_time = timezone.now()

		if win == 'white' or win == self.white_player:
			self.winner = self.white_player
		elif win == 'black' or win == self.black_player:
			self.winner = self.black_player
		else:
			self.winner = None

		self.white_player_score = self.result_score('white', self.winner)
		self.black_player_score = self.result_score('black', self.winner)
		self.white_player.score += self.white_player_score
		self.black_player.score += self.black_player_score

		self.ended = True
		self.playing = False

		if self.movement_count > 0:
			timedelta = (self.end_time - self.last_movement_time).total_seconds()
			if self.color == 'white':
				self.white_player_time += timedelta
			else:
				self.black_player_time += timedelta
		self.last_movement_time = self.end_time

		self.end_reason = res
		self.save()

	def get_color_by_user(self, user: 'User') -> str:
		if self.white_player == user:
			return 'white'
		elif self.black_player == user:
			return 'black'

	def get_user_by_color(self, color: str) -> 'User':
		if color == 'white':
			return self.white_player
		elif color == 'black':
			return self.black_player

	def get_opponent_user(self, user: 'User') -> 'User':
		if user == self.white_player:
			return self.black_player
		elif user == self.black_player:
			return self.white_player

	@staticmethod
	def board_movement(movement: list) -> str:
		matrix = value_matrix('[]', 8, 8)

		for y, line in enumerate(movement):
			for x, piece in enumerate(line):
				parts = piece.split(' ')
				if len(parts) == 2:
					if parts[1] in ['black','white']:
						match parts[0]:
							case 'Pawn':
								matrix[y][x] = 'p' + parts[1][0]
							case 'Rook':
								matrix[y][x] = 'r' + parts[1][0]
							case 'Knight':
								matrix[y][x] = 'k' + parts[1][0]
							case 'Bishop':
								matrix[y][x] = 'b' + parts[1][0]
							case 'Queen':
								matrix[y][x] = 'Q' + parts[1][0]
							case 'King':
								matrix[y][x] = 'K' + parts[1][0]
		return '.' + '.'.join([ '.'.join(line)+'\n' for line in matrix ])

	@staticmethod
	def predict_result(user1: 'User', user2: 'User') -> int:
		predict_score = lambda r1, r2: 1 / ( 1 + 10 * (r2 - r1) / 400 )
		return predict_score(user1.score, user2.score), predict_score(user2.score, user1.score)

	def result_score(self, color: str, winner_color: str) -> int:
		user = self.get_user_by_color(color)
		opponent = self.get_opponent_user(user)

		k = 10 if user.score >= 2400 else (40 if user.games_count <= 30 else 20)
		s = 1 if winner_color == color else (0.5 if winner_color == None else 0)

		return k * (s + self.__class__.predict_result(user, opponent)[0])

	def all_pieces_movements(self, color: str = None, return_dict: bool = False) -> list: # these are the available movements taking into account check for the king
		res = list(set([
			tuple([ (tuple(piece.pos), tuple(pos)) for pos in piece.movable_to(
				enemies=self.black_pieces if piece.color == 'white' else self.white_pieces,
				friends=self.black_pieces if piece.color == 'black' else self.white_pieces)
			])
			for piece in self.alive_pieces if len(piece.movable_to(
				enemies=self.black_pieces if piece.color == 'white' else self.white_pieces,
				friends=self.black_pieces if piece.color == 'black' else self.white_pieces)
			) != 0 and ( piece.color == color if color != None else True )
		]))
		list_res = []
		res_dict = {}

		for movement in res:
			for m in movement:
				list_res.append(m)

		if return_dict:
			for piece, to in list_res:
				if piece in res_dict.keys():
					res_dict[piece] = res_dict[piece] + (to,)
				else:
					res_dict[piece] = (to,)

		return res_dict if return_dict else list_res

	def lost_pieces_by_color(self, color: str) -> list:
		return [ eval(f"{piece.split(' ')[0]}('{piece.split(' ')[1]}')") for piece in self.destroyed_pieces if piece.split(' ')[1] == color ]

	def get_king_by_color(self):
		return [ king for king in self.kings if king.color == color]

	@property
	def color(self) -> str:
		if len(self.movements) % 2:
			return 'white'
		else:
			return 'black'

	@property
	def movement_count(self) -> int:
		return len(self.movements)-1

	@property
	def kings(self):
		return [ piece for piece in self.alive_pieces if isinstance(piece, King) ]

	@property
	def black_king(self):
		return [ king for king in self.kings if king.color == 'black']
	@property
	def white_king(self):
		return [ king for king in self.kings if king.color == 'white']

	@property
	def alive_pieces(self) -> list:
		res = []
		for y in self.soft_movements[-1]:
			for piece in y:
				if isinstance(piece, Piece):
					res.append(piece)
		return res

	@property
	def black_pieces(self) -> list:
		res = []
		for piece in self.alive_pieces:
			if piece.color == 'black':
				res.append(piece)
		return res

	@property
	def white_pieces(self) -> list:
		res = []
		for piece in self.alive_pieces:
			if piece.color == 'white':
				res.append(piece)
		return res

	@property
	def soft_movements(self) -> list:
		return str_to_movements(self.movements)

	@property
	def board(self) -> str:
		return Game.board_movement(self.movements[-1])

	@property
	def players(self) -> list:
		return [self.white_player, self.black_player]

	@property
	def starting(self) -> bool:
		return len(self.movements) == 1 and not self.playing

	def __getitem__(self, pos) -> list:
		if isinstance(pos, int):
			return [ self.soft_movements[-1][y][pos] for y in range(8) ]
		elif isinstance(pos, (tuple, list)):
			return self.soft_movements[-1][pos[1]][pos[0]]
		elif pos == 'black':
			return self.black_pieces
		elif pos == 'white':
			return self.white_pieces
		elif pos == 'alive':
			return self.alive_pieces
		elif pos == 'destroyed':
			return self.destroyed_pieces
		else:
			raise ValueError(f'__getitem__ argument must be int (position by x), tuple/list (position by [x,y]), or "black"/"white"/"alive"/"destroyed" to get pieces')

	def __len__(self):
		return len(self.movements)
	def __str__(self):
		return f"Game({len(self)} movements, {'the game continues' if self.playing else 'the game is paused or finished'}, next movement: {self.color})"
	def __list__(self):
		return list(self.movements)
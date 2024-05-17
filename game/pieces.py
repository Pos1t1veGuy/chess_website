def pos_at_board(pos: list) -> bool:
	if len(pos) == 2:
		if isinstance(pos[0], int) and isinstance(pos[1], int):
			return 0 <= pos[0] <= 7 and 0 <= pos[1] <= 7
	
	raise ValueError(f"'pos' must contain only 2 int from 0 to 7, not {pos}")

class Piece:
	def __init__(self, color: str, pos: list = [0,0]):
		self.price = 1
		if color in ['black', 'white']:
			self.color = color
		else:
			raise ValueError(f"'color' must be string 'black' or 'white', not {color}")

		if pos_at_board(pos):
			self.pos = pos
			self.last_pos = pos
		else:
			raise ValueError(f"'pos' must be position in rectangle from [0,0] to [7,7], not {pos}")

		self.destroyed = False
		self.moved = False
		self.last_moved = False

	def move(self, pos: list, movable_to: list = []):
		if list(pos) in movable_to and pos_at_board(pos):
			self.last_pos = self.pos.copy()
			self.last_moved = self.moved
			self.pos = pos
			self.moved = True
		else:
			raise ValueError(f"Piece {self.__class__.__name__} at {self.pos} can not move to {pos}")

	def undo(self):
		if self.last_pos:
			self.pos = self.last_pos.copy()
		if self.last_moved:
			self.moved = self.last_moved.copy()

	def set_pos(self, pos: list):
		self.pos = pos
		self.moved = True

	@property
	def x(self) -> int:
		return self.pos[0]
	@property
	def y(self) -> int:
		return self.pos[1]


	@staticmethod
	def if_not_destroyed(func):
		def wrapper(self, *args, **kwargs):
			if self.destroyed:
				raise ValueError("The piece has destroyed")
			return func(self, *args, **kwargs)
		return wrapper

	def __str__(self):
		return f'{self.__class__.__name__} {self.color}'

class Pawn(Piece):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	@Piece.if_not_destroyed
	def move(self, pos: list, enemies: list = [], friends: list = []):
		super().move(pos, movable_to=self.movable_to(enemies=enemies, friends=friends))

	@Piece.if_not_destroyed
	def movable_to(self, enemies: list = [], friends: list = []) -> list:
		enemy_positions = [ piece.pos for piece in enemies ]
		movable_to = []

		if self.color == 'black':
			movable_to = [
				[self.pos[0], self.pos[1]+1]
			]
			if self.pos[1] == 1:
				movable_to += [[self.pos[0], self.pos[1]+2]]

			if [self.pos[0]+1, self.pos[1]+1] in enemy_positions:
				movable_to += [[self.pos[0]+1, self.pos[1]+1]]
			if [self.pos[0]-1, self.pos[1]+1] in enemy_positions:
				movable_to += [[self.pos[0]-1, self.pos[1]+1]]
		else:
			movable_to = [
				[self.pos[0], self.pos[1]-1]
			]
			if self.pos[1] == 6:
				movable_to += [[self.pos[0], self.pos[1]-2]]

			if [self.pos[0]+1, self.pos[1]-1] in enemy_positions:
				movable_to += [[self.pos[0]+1, self.pos[1]-1]]
			if [self.pos[0]-1, self.pos[1]-1] in enemy_positions:
				movable_to += [[self.pos[0]-1, self.pos[1]-1]]

		if self.pos in movable_to:
			movable_to.remove(self.pos)

		for friend in friends:
			if friend.pos in movable_to:
				movable_to.remove(friend.pos)

		return movable_to

class Rook(Piece):
	def __init__(self, *args, **kwargs):
		self.price = 5
		super().__init__(*args, **kwargs)
		
	@Piece.if_not_destroyed
	def move(self, pos: list, enemies: list = [], friends: list = []):
		super().move(pos, movable_to=self.movable_to(enemies=enemies, friends=friends))

	@Piece.if_not_destroyed
	def movable_to(self, enemies: list = [], friends: list = []) -> list:
		enemy_positions = [ piece.pos for piece in enemies ]

		enemy_at_x = [ epos[0] for epos in enemy_positions if epos[1] == self.pos[1] ]
		enemy_min_x = max([ x for x in enemy_at_x if x < self.pos[0] ]) if [ x for x in enemy_at_x if x < self.pos[0] ] else 0
		enemy_max_x = min([ x for x in enemy_at_x if x > self.pos[0] ]) if [ x for x in enemy_at_x if x > self.pos[0] ] else 7

		enemy_at_y = [ epos[1] for epos in enemy_positions if epos[0] == self.pos[0] ]
		enemy_min_y = max([ y for y in enemy_at_y if y < self.pos[0] ]) if [ y for y in enemy_at_y if y < self.pos[0] ] else 0
		enemy_max_y = min([ y for y in enemy_at_y if y > self.pos[0] ]) if [ y for y in enemy_at_y if y > self.pos[0] ] else 7

		friend_positions = [ piece.pos for piece in friends ]

		friend_at_x = [ fpos[0] for fpos in friend_positions if fpos[1] == self.pos[1] ]
		friend_min_x = max([ x for x in friend_at_x if x < self.pos[0] ]) if [ x for x in friend_at_x if x < self.pos[0] ] else 0
		friend_max_x = min([ x for x in friend_at_x if x > self.pos[0] ]) if [ x for x in friend_at_x if x > self.pos[0] ] else 7

		friend_at_y = [ fpos[1] for fpos in friend_positions if fpos[0] == self.pos[0] ]
		friend_min_y = max([ y for y in friend_at_y if y < self.pos[1] ]) if [ y for y in friend_at_y if y < self.pos[1] ] else 0
		friend_max_y = min([ y for y in friend_at_y if y > self.pos[1] ]) if [ y for y in friend_at_y if y > self.pos[1] ] else 7

		max_x, min_x = min(enemy_max_x, friend_max_x-1), max(enemy_min_x, friend_min_x+1)
		max_y, min_y = min(enemy_max_y, friend_max_y-1), max(enemy_min_y, friend_min_y)

		movable_to = []
		for x in range(min_x, max_x+1):
			if self.pos != [x, self.pos[1]]:
				movable_to.append([x, self.pos[1]])
		for y in range(min_y, max_y+1):
			if self.pos != [self.pos[0], y]:
				movable_to.append([self.pos[0], y])

		return movable_to

class Bishop(Piece):
	def __init__(self, *args, **kwargs):
		self.price = 3
		super().__init__(*args, **kwargs)
		
	@Piece.if_not_destroyed
	def move(self, pos: list, enemies: list = [], friends: list = []):
		super().move(pos, movable_to=self.movable_to(enemies=enemies, friends=friends))

	@Piece.if_not_destroyed
	def movable_to(self, enemies: list = [], friends: list = []) -> list:
		enemy_positions = [ piece.pos for piece in enemies ]
		friend_positions = [ piece.pos for piece in friends ]
		movable_to = []

		for i in [1, -1]:
			max_pos1, max_pos2 = self.pos, self.pos

			# if self.pos == [4,6]:
			# 	print(max_pos1, 'in', enemy_positions)
			while pos_at_board([max_pos1[0]+1*i, max_pos1[1]+1*i]) and not max_pos1 in enemy_positions:
				#print(self.pos, 1)
				if [max_pos1[0]+1*i, max_pos1[1]+1*i] in friend_positions:
					max_pos1 = [0, 0]
					break
				movable_to.append([max_pos1[0]+1*i, max_pos1[1]+1*i])
				max_pos1 = [max_pos1[0]+1*i, max_pos1[1]+1*i]

			# if self.pos == [4,6]:
			# 	print(max_pos2, 'in', enemy_positions)
			while pos_at_board([max_pos2[0]-1*i, max_pos2[1]+1*i]) and not max_pos2 in enemy_positions:
				#print(self.pos, 2)
				if [max_pos2[0]-1*i, max_pos2[1]+1*i] in friend_positions:
					max_pos2 = [0, 0]
					break
				movable_to.append([max_pos2[0]-1*i, max_pos2[1]+1*i])
				max_pos2 = [max_pos2[0]-1*i, max_pos2[1]+1*i]

		#print('!', self.pos, movable_to, '\n&', enemy_positions, friend_positions)
		return movable_to

class Knight(Piece):
	def __init__(self, *args, **kwargs):
		self.price = 3
		super().__init__(*args, **kwargs)
		
	@Piece.if_not_destroyed
	def move(self, pos: list, enemies: list = [], friends: list = []):
		super().move(pos, movable_to=self.movable_to(enemies=enemies, friends=friends))

	@Piece.if_not_destroyed
	def movable_to(self, enemies: list = [], friends: list = []) -> list:
		friend_positions = [ piece.pos for piece in friends ]
		movable_to = [ pos for pos in [
			[self.pos[0]-2, self.pos[1]-1],
			[self.pos[0]-2, self.pos[1]+1],
			[self.pos[0]+2, self.pos[1]-1],
			[self.pos[0]+2, self.pos[1]+1],

			[self.pos[0]-1, self.pos[1]-2],
			[self.pos[0]+1, self.pos[1]-2],
			[self.pos[0]-1, self.pos[1]+2],
			[self.pos[0]+1, self.pos[1]+2],
		] if pos_at_board(pos) and not pos in friend_positions ]

		return movable_to

class Queen(Piece):
	def __init__(self, *args, **kwargs):
		self.price = 9
		super().__init__(*args, **kwargs)
		
	@Piece.if_not_destroyed
	def move(self, pos: list, enemies: list = [], friends: list = []):
		super().move(pos, movable_to=self.movable_to(enemies=enemies, friends=friends))

	@Piece.if_not_destroyed
	def movable_to(self, enemies: list = [], friends: list = []) -> list:
		enemy_positions = [ piece.pos for piece in enemies ]
		friend_positions = [ piece.pos for piece in friends ]
		movable_to = []

		enemy_at_x = [ epos[0] for epos in enemy_positions if epos[1] == self.pos[1] ]
		enemy_min_x = max([ x for x in enemy_at_x if x < self.pos[0] ]) if [ x for x in enemy_at_x if x < self.pos[0] ] else 0
		enemy_max_x = min([ x for x in enemy_at_x if x > self.pos[0] ]) if [ x for x in enemy_at_x if x > self.pos[0] ] else 7

		enemy_at_y = [ epos[1] for epos in enemy_positions if epos[0] == self.pos[0] ]
		enemy_min_y = max([ y for y in enemy_at_y if y < self.pos[0] ]) if [ y for y in enemy_at_y if y < self.pos[0] ] else 0
		enemy_max_y = min([ y for y in enemy_at_y if y > self.pos[0] ]) if [ y for y in enemy_at_y if y > self.pos[0] ] else 7

		friend_at_x = [ fpos[0] for fpos in friend_positions if fpos[1] == self.pos[1] ]
		friend_min_x = max([ x for x in friend_at_x if x < self.pos[0] ]) if [ x for x in friend_at_x if x < self.pos[0] ] else 0
		friend_max_x = min([ x for x in friend_at_x if x > self.pos[0] ]) if [ x for x in friend_at_x if x > self.pos[0] ] else 7

		friend_at_y = [ fpos[1] for fpos in friend_positions if fpos[0] == self.pos[0] ]
		friend_min_y = max([ y for y in friend_at_y if y < self.pos[1] ]) if [ y for y in friend_at_y if y < self.pos[1] ] else 0
		friend_max_y = min([ y for y in friend_at_y if y > self.pos[1] ]) if [ y for y in friend_at_y if y > self.pos[1] ] else 7

		max_x, min_x = min(enemy_max_x, friend_max_x-1), max(enemy_min_x, friend_min_x+1)
		max_y, min_y = min(enemy_max_y, friend_max_y-1), max(enemy_min_y, friend_min_y)

		for x in range(min_x, max_x+1):
			if self.pos != [x, self.pos[1]]:
				movable_to.append([x, self.pos[1]])
		for y in range(min_y, max_y+1):
			if self.pos != [self.pos[0], y]:
				movable_to.append([self.pos[0], y])

		for i in [1, -1]:
			max_pos1, max_pos2 = self.pos, self.pos

			while pos_at_board([max_pos1[0]+1*i, max_pos1[1]+1*i]) and not max_pos1 in enemy_positions:
				if [max_pos1[0]+1*i, max_pos1[1]+1*i] in friend_positions:
					max_pos1 = [0, 0]
					break
				movable_to.append([max_pos1[0]+1*i, max_pos1[1]+1*i])
				max_pos1 = [max_pos1[0]+1*i, max_pos1[1]+1*i]

			while pos_at_board([max_pos2[0]-1*i, max_pos2[1]+1*i]) and not max_pos2 in enemy_positions:
				if [max_pos2[0]-1*i, max_pos2[1]+1*i] in friend_positions:
					max_pos2 = [0, 0]
					break
				movable_to.append([max_pos2[0]-1*i, max_pos2[1]+1*i])
				max_pos2 = [max_pos2[0]-1*i, max_pos2[1]+1*i]

		return movable_to

class King(Piece):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.mate = False
		self.check = False

	@Piece.if_not_destroyed
	def move(self, pos: list, enemies: list = [], friends: list = []):
		super().move(pos, movable_to=self.movable_to(enemies=enemies, friends=friends))

	@Piece.if_not_destroyed
	def movable_to(self, enemies: list = [], friends: list = []) -> list:
		self.check = False
		enemy_positions = [ piece.pos for piece in enemies ]
		friend_positions = [ piece.pos for piece in friends ]
		movable_to = [ pos for pos in [
			[self.pos[0], self.pos[1]+1],   # 111 #
			[self.pos[0]+1, self.pos[1]+1], # 101 #
			[self.pos[0]+1, self.pos[1]],   # 111 #
			[self.pos[0]+1, self.pos[1]-1],
			[self.pos[0], self.pos[1]-1],
			[self.pos[0]-1, self.pos[1]-1],
			[self.pos[0]-1, self.pos[1]],
			[self.pos[0]-1, self.pos[1]+1],
		] if pos_at_board(pos) and not pos in enemy_positions + friend_positions]

		self.mate = len(movable_to) == 0
		return movable_to

	def check(self, enemies: list = [], friends: list = []):
		return self.pos in [ piece.movable_to for piece in enemies ]
	def mate(self, enemies: list = [], friends: list = []):
		return len(self.movable_to(enemies=enemies, friends=friends)) == 0

	def check_enemies(self, enemies: list = [], friends: list = []):
		return [ piece for piece in enemies if self.pos in piece.movable_to(friends, enemies) ]

	@property
	def checkmate(self):
		return self.check and self.mate
from random import getrandbits
from model.ActionType import ActionType
from model.Direction import Direction
from model.Game import Game
from model.Move import Move
from model.Trooper import Trooper
from model.TrooperStance import TrooperStance
from model.World import World


class MyStrategy:
    def move(self, me, world, game, move):
        if me.action_points < game.standing_move_cost:
            return

        move.action = ActionType.MOVE

        if getrandbits(1):
            move.direction = Direction.NORTH if getrandbits(1) else Direction.SOUTH
        else:
            move.direction = Direction.WEST if getrandbits(1) else Direction.EAST
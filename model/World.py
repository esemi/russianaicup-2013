from math import *
from TrooperStance import TrooperStance


class World:
    def __init__(self, move_index, width, height, players, troopers, bonuses, cells, cell_visibilities):
        self.move_index = move_index
        self.width = width
        self.height = height
        self.players = players
        self.troopers = troopers
        self.bonuses = bonuses
        self.cells = cells
        self.cell_visibilities = cell_visibilities
        
        self.stance_count = 0
        
        for enum_key, enum_value in TrooperStance.__dict__.items():
            if not str(enum_key).startswith("__"):
                self.stance_count += 1

    def is_visible(self, max_range,
                   viewer_x, viewer_y, viewer_stance,
                   object_x, object_y, object_stance):
        min_stance_index = min(viewer_stance, object_stance)
        x_range = object_x - viewer_x
        y_range = object_y - viewer_y
        
        return x_range * x_range + y_range * y_range <= max_range * max_range and ord(self.cell_visibilities[
            viewer_x * self.height * self.width * self.height * self.stance_count
            + viewer_y * self.width * self.height * self.stance_count
            + object_x * self.height * self.stance_count
            + object_y * self.stance_count
            + min_stance_index
        ]) == 1
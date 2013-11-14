from ActionType import ActionType


class Move:
    def __init__(self):
        self.action = ActionType.END_TURN
        self.direction = None
        self.x = -1
        self.y = -1
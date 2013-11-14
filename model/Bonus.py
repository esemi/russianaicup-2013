from Unit import Unit


class Bonus(Unit):
    def __init__(self, id, x, y, type):
        Unit.__init__(self, id, x, y)

        self.type = type
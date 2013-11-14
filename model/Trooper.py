from Unit import Unit
from model.TrooperStance import TrooperStance


class Trooper(Unit):
    def __init__(self, id, x, y, player_id,
                 teammate_index, teammate, type, stance,
                 hitpoints, maximal_hitpoints, action_points, initial_action_points,
                 vision_range, shooting_range, shoot_cost,
                 standing_damage, kneeling_damage, prone_damage, damage,
                 holding_grenade, holding_medikit, holding_field_ration):
        Unit.__init__(self, id, x, y)

        self.player_id = player_id
        self.teammate_index = teammate_index
        self.teammate = teammate
        self.type = type
        self.stance = stance
        self.hitpoints = hitpoints
        self.maximal_hitpoints = maximal_hitpoints
        self.action_points = action_points
        self.initial_action_points = initial_action_points
        self.vision_range = vision_range
        self.shooting_range = shooting_range
        self.shoot_cost = shoot_cost
        self.standing_damage = standing_damage
        self.kneeling_damage = kneeling_damage
        self.prone_damage = prone_damage
        self.damage = damage
        self.holding_grenade = holding_grenade
        self.holding_medikit = holding_medikit
        self.holding_field_ration = holding_field_ration

    def get_damage(self, stance):
        if stance == TrooperStance.PRONE:
            return self.prone_damage
        if stance == TrooperStance.KNEELING:
            return self.kneeling_damage
        if stance == TrooperStance.STANDING:
            return self.standing_damage
        raise ValueError("Unsupported stance: %s." % stance)
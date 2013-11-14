class Game:
    def __init__(self, move_count,
                 last_player_elimination_score, player_elimination_score,
                 trooper_elimination_score, trooper_damage_score_factor,
                 stance_change_cost, standing_move_cost, kneeling_move_cost, prone_move_cost,
                 commander_aura_bonus_action_points, commander_aura_range,
                 commander_request_enemy_disposition_cost, commander_request_enemy_disposition_max_offset,
                 field_medic_heal_cost, field_medic_heal_bonus_hitpoints, field_medic_heal_self_bonus_hitpoints,
                 sniper_standing_stealth_bonus, sniper_kneeling_stealth_bonus, sniper_prone_stealth_bonus,
                 sniper_standing_shooting_range_bonus, sniper_kneeling_shooting_range_bonus,
                 sniper_prone_shooting_range_bonus, scout_stealth_bonus_negation,
                 grenade_throw_cost, grenade_throw_range, grenade_direct_damage, grenade_collateral_damage,
                 medikit_use_cost, medikit_bonus_hitpoints, medikit_heal_self_bonus_hitpoints,
                 field_ration_eat_cost, field_ration_bonus_action_points):
        self.move_count = move_count
        self.last_player_elimination_score = last_player_elimination_score
        self.player_elimination_score = player_elimination_score
        self.trooper_elimination_score = trooper_elimination_score
        self.trooper_damage_score_factor = trooper_damage_score_factor
        self.stance_change_cost = stance_change_cost
        self.standing_move_cost = standing_move_cost
        self.kneeling_move_cost = kneeling_move_cost
        self.prone_move_cost = prone_move_cost
        self.commander_aura_bonus_action_points = commander_aura_bonus_action_points
        self.commander_aura_range = commander_aura_range
        self.commander_request_enemy_disposition_cost = commander_request_enemy_disposition_cost
        self.commander_request_enemy_disposition_max_offset = commander_request_enemy_disposition_max_offset
        self.field_medic_heal_cost = field_medic_heal_cost
        self.field_medic_heal_bonus_hitpoints = field_medic_heal_bonus_hitpoints
        self.field_medic_heal_self_bonus_hitpoints = field_medic_heal_self_bonus_hitpoints
        self.sniper_standing_stealth_bonus = sniper_standing_stealth_bonus
        self.sniper_kneeling_stealth_bonus = sniper_kneeling_stealth_bonus
        self.sniper_prone_stealth_bonus = sniper_prone_stealth_bonus
        self.sniper_standing_shooting_range_bonus = sniper_standing_shooting_range_bonus
        self.sniper_kneeling_shooting_range_bonus = sniper_kneeling_shooting_range_bonus
        self.sniper_prone_shooting_range_bonus = sniper_prone_shooting_range_bonus
        self.scout_stealth_bonus_negation = scout_stealth_bonus_negation
        self.grenade_throw_cost = grenade_throw_cost
        self.grenade_throw_range = grenade_throw_range
        self.grenade_direct_damage = grenade_direct_damage
        self.grenade_collateral_damage = grenade_collateral_damage
        self.medikit_use_cost = medikit_use_cost
        self.medikit_bonus_hitpoints = medikit_bonus_hitpoints
        self.medikit_heal_self_bonus_hitpoints = medikit_heal_self_bonus_hitpoints
        self.field_ration_eat_cost = field_ration_eat_cost
        self.field_ration_bonus_action_points = field_ration_bonus_action_points
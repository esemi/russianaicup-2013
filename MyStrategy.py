#! /usr/bin/env python
# -*- coding: utf-8 -*-


import logging

import copy
from math import *
from random import shuffle

import SharedVars as shared

from model.ActionType import ActionType
from model.TrooperStance import TrooperStance
from model.TrooperType import TrooperType
from model.CellType import CellType
from model.BonusType import BonusType


# коэф. для вычисления максимальной дальности юнита от точки базирования команды
CF_range_from_team = 1.1
CF_range_from_team_medic = 0.9

# коэф. для вычисления максимальной дальности юнита от вейпоинта
CF_range_from_waypoint = 0.5

# уровень здоровья юнита, при котором он получает приоритет на лечение
CF_medic_heal_level = 0.7

# множитель для минимума недостающих хитов здоровья юнита при решении использовать аптечку или нет
CF_medkit_bonus_hits = 0.8

# радиус обзора, в пределах которого юниты кидаются за бонусом
CF_range_bonus_for_me = 3.0


def log_it(msg, level='info'):
    getattr(logging, level)(msg)


def distance_from_to(coord_from, coord_to):
    return hypot(coord_to[0] - coord_from[0], coord_to[1] - coord_from[1])


def filter_free_wave(map_, val=None):
    if val is None:
        func = lambda x: (x['wave_num'] is None)
    else:
        func = lambda x: (x['wave_num'] == val)

    waves = []
    for row in map_:
        waves += filter(func, row)

    return filter(lambda x: x['passability'], waves)


def find_cell_neighborhood(coord, map_, allow_diagonaly=False):
    out = []

    if coord[0] > 0:
        try:
            out.append(map_[coord[0]-1][coord[1]])
        except IndexError:
            pass

    try:
        out.append(map_[coord[0]+1][coord[1]])
    except IndexError:
        pass

    if coord[1] > 0:
        try:
            out.append(map_[coord[0]][coord[1]-1])
        except IndexError:
            pass

    try:
        out.append(map_[coord[0]][coord[1]+1])
    except IndexError:
        pass

    if allow_diagonaly:
        try:
            out.append(map_[coord[0]+1][coord[1]+1])
        except IndexError:
            pass

        if coord[0] > 0:
            try:
                out.append(map_[coord[0]-1][coord[1]+1])
            except IndexError:
                pass

        if coord[1] > 0:
            try:
                out.append(map_[coord[0]+1][coord[1]-1])
            except IndexError:
                pass

        if coord[0] > 0 and coord[1] > 0:
            try:
                out.append(map_[coord[0]-1][coord[1]-1])
            except IndexError:
                pass

    return filter(lambda x: x['passability'], out)


def get_waypoint_near_of_coord(cells, coord):
    """
    Возвращаем координаты свободного вейпоинта поблизости от требуемых координат

    """

    map_ = []
    for x, row in enumerate(cells):
        for y, v in enumerate(row):
            if v == CellType.FREE:
                map_.append(dict(coord=(x, y), distance=distance_from_to(coord, (x, y))))
    return sorted(map_, key=lambda x: x['distance'])[0]['coord']


class MyStrategy:

    def __init__(self):
        self.current_path = None
        logging.basicConfig(
            format='%(asctime)s %(levelname)s:%(message)s',
            level=logging.INFO)

    def move(self, me, world, game, move):
        log_it('<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
        log_it('new move turn %d unit %d (%s)' % (world.move_index, me.id, str((me.x, me.y))))

        if shared.way_points is None:
            self._compute_waypoints(world)

        self._action_base(me, world, game, move)
        log_it('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')

    @property
    def current_path(self):
        return self._current_path

    @current_path.setter
    def current_path(self, value):
        self._current_path = value

    @staticmethod
    def select_action_by_type(type_):
        if type_ == TrooperType.FIELD_MEDIC:
            return '_action_medic'
        else:
            return '_action_commander'

    @staticmethod
    def team_avg_coord(world):
        """
        Вычисляем координаты точки базирования отряда (среднее значение координат)

        """

        current_x = [t.x for t in world.troopers if t.teammate]
        current_y = [t.y for t in world.troopers if t.teammate]
        return int(sum(current_x) / len(current_x)), int(sum(current_y) / len(current_y))

    @staticmethod
    def team_avg_shooting_range(world):
        """
        Вычисляем среднюю дальность стрельбы отряда

        """

        ranges = [t.shooting_range for t in world.troopers if t.teammate]
        return sum(ranges) / len(ranges)

    def _compute_waypoints(self, world):
        """
        Вычисляем waypoint-ы - сперва все углы прямоугольной карты а в конец добавляем координаты центра
        берём только свободные от препятствий точки на карте (в окресностях углов и центра)

        """

        current_coord = self.team_avg_coord(world)
        log_it("compute current command coord %s" % str(current_coord))

        center_coord = get_waypoint_near_of_coord(world.cells, (int(world.width / 2), int(world.height / 2)))

        angles = [
            get_waypoint_near_of_coord(world.cells, (0, 0)),
            get_waypoint_near_of_coord(world.cells, (0, world.height - 1)),
            get_waypoint_near_of_coord(world.cells, (world.width - 1, world.height - 1)),
            get_waypoint_near_of_coord(world.cells, (world.width - 1, 0))]

        sorted_waypoints = []
        for k in xrange(len(angles)):
            if k == 0:
                angles = sorted(angles, key=lambda i: distance_from_to(current_coord, i))
            else:
                angles = sorted(angles, key=lambda i: distance_from_to(sorted_waypoints[k-1], i))
            sorted_waypoints.append(angles.pop(0))

        sorted_waypoints.append(center_coord)
        shared.way_points = sorted_waypoints
        log_it('select %s waypoints' % str(sorted_waypoints))

    @staticmethod
    def change_current_waypoint(me):
        """
        Если юнит достиг видимости вейпоинта - выбирает следующий вейпоинт
        Если вейпоинт ещё не задан - берёт первый из списка
        Если достигнут последний вейпоинт - удерживаем позицию (каждый солдат сам решает как лучше удерживать)
        """

        log_it("current dest waypoint is %s" % str(shared.current_dest_waypoint))

        if shared.current_dest_waypoint is None:
            shared.current_dest_waypoint = 0

        if len(shared.way_points) > shared.current_dest_waypoint + 1:
            distance_to_waypoint = me.get_distance_to(*shared.way_points[shared.current_dest_waypoint])
            if distance_to_waypoint < me.vision_range * CF_range_from_waypoint:
                shared.current_dest_waypoint += 1
                log_it("new dest waypoint is %s" % str(shared.current_dest_waypoint))

    def max_range_from_team_exceeded(self, world, me):
        """
        Проверяем - не ушёл ли юнит слишком далеко от отряда:

        """

        shoot_range = self.team_avg_shooting_range(world)
        ranges_to_team = [me.get_distance_to(t.x, t.y) for t in world.troopers if t.teammate and t.id != me.id]
        coef = CF_range_from_team if me.type != TrooperType.FIELD_MEDIC else CF_range_from_team_medic
        if len(ranges_to_team) == 0:
            return False
        else:
            return max(ranges_to_team) > shoot_range * coef

    @staticmethod
    def need_to_wait_medic(me, world):
        return me.type != TrooperType.FIELD_MEDIC and me.hitpoints < me.maximal_hitpoints and \
               len([t for t in world.troopers if t.teammate and t.type == TrooperType.FIELD_MEDIC]) == 1

    @staticmethod
    def could_and_need_use_ration(me, game):
        return me.action_points >= game.field_ration_eat_cost and me.holding_field_ration

    @staticmethod
    def could_and_need_use_grenade(me, enemy, game, world):

        # проверяем, не заденем ли мы союзных юнитов
        map_passability = [[dict(coord=(x, y), passability=(v == CellType.FREE)) for y, v in enumerate(row)]
                           for x, row in enumerate(world.cells)]
        damage_cells = [c['coord'] for c in find_cell_neighborhood((enemy.x, enemy.y), map_passability)]
        if len([t for t in world.troopers if t.teammate and (t.x, t.y) in damage_cells]) > 0:
            log_it('not use grenade (team units are damaged)')
            return False

        return me.action_points >= game.grenade_throw_cost and me.holding_grenade and \
               world.is_visible(game.grenade_throw_range, me.x, me.y, me.stance, enemy.x, enemy.y, enemy.stance)

    def find_bonus(self, me, world):
        """
        Выбираем бонусы для подбора данным юнитом
        проверяем, что не выйдем за оперативный радиус команды, пока идём до бонуса

        """

        holding_types = []
        if me.holding_grenade:
            holding_types.append(BonusType.GRENADE)
        if me.holding_medikit:
            holding_types.append(BonusType.MEDIKIT)
        if me.holding_field_ration:
            holding_types.append(BonusType.FIELD_RATION)

        bonuses = filter(lambda b: not self.max_range_from_team_exceeded(world, b) and b.type not in holding_types and
                                   me.get_distance_to_unit(b) <= CF_range_bonus_for_me, world.bonuses)

        if len(bonuses) > 0:
            return sorted(bonuses, key=lambda b: me.get_distance_to_unit(b))[0]
        else:
            return None

    @staticmethod
    def could_and_need_use_medikit(me, heal_enemy, game):
        heal_bonus = game.field_medic_heal_bonus_hitpoints * CF_medkit_bonus_hits if me.id != heal_enemy.id else \
            game.field_medic_heal_self_bonus_hitpoints

        return me.action_points >= game.medikit_use_cost and me.holding_medikit and \
               (heal_enemy.maximal_hitpoints - heal_enemy.hitpoints) >= heal_bonus

    @staticmethod
    def heal_avaliable(me, enemy):
        return me.get_distance_to(enemy.x, enemy.y) <= 1.0

    @staticmethod
    def cell_free_for_move(coord, world):
        troopers_coord = [t for t in world.troopers if (t.x, t.y) == coord]
        return world.cells[coord[0]][coord[1]] == CellType.FREE and len(troopers_coord) == 0

    def select_heal_enemy(self, me, world):
        """
        Выбираем союзника для лечения: выбираем ближайшего с неполными хитами

        :rtype Trooper or None
        """

        units_for_heal = [t for t in world.troopers if t.teammate and t.hitpoints < t.maximal_hitpoints]
        if len(units_for_heal) == 0:
            return None

        log_it('find %d units for heal' % len(units_for_heal))

        avaliable_for_heal = filter(lambda x: self.heal_avaliable(me, x) and
                                    (x.hitpoints / x.maximal_hitpoints) < CF_medic_heal_level, units_for_heal)

        if len(avaliable_for_heal) > 0:  # берём соседа с минимальным здоровьем
            log_it('find %d heal neighborhoods' % len(avaliable_for_heal))
            return sorted(avaliable_for_heal, key=lambda e: e.hitpoints)[0]
        else:
            return sorted(units_for_heal, key=lambda u: me.get_distance_to(u.x, u.y))[0]

    def select_position_for_medic(self, me, world):
        """
        Выбираем позицию для хиллера, при атакующей остальной команде
        берём всех солдат, ищем вокруг них свободные клетки (только от препятствий)
        выбираем из клеток ту, которая находится в зоне обстрела врагов меньше всего

        """

        troopers = [t for t in world.troopers if t.teammate and t.id != me.id]
        map_passability = [[dict(coord=(x, y), passability=(v == CellType.FREE)) for y, v in enumerate(row)]
                           for x, row in enumerate(world.cells)]

        cells = []
        for t in troopers:
            cells += find_cell_neighborhood((t.x, t.y), map_passability, True)
        sorted_coords = sorted([c['coord'] for c in cells], key=lambda e: self.cell_attack_rank(e, world))

        if len(sorted_coords) > 0:
            return sorted_coords[0]
        else:
            log_it('not found cells for medic safe staying %s %s' % (str(cells), str(troopers)), 'error')
            return None

    def select_enemy(self, me, world):
        """
        Выбираем врага в поле видимости команды
        если в текущем поле досягаемости оружия есть враг и мы можем убить его за оставшиеся ходы - берём его
        иначе ищем врагов в поле видимости команды
            если враги есть - берём ближайшего к центру команды из них
            иначе - None

        :rtype Trooper or None
        """

        enemies = [t for t in world.troopers if not t.teammate]
        if len(enemies) == 0:
            return None

        # проверяем, нет ли среди ближайших врагов такого, которого можно было бы атаковать
        visible_enemies = [e for e in enemies if world.is_visible(me.shooting_range, me.x, me.y, me.stance, e.x, e.y,
                                                                  e.stance)]
        sorted_visible_enemies = sorted(visible_enemies, key=lambda e: e.hitpoints)

        # если в досягаемости есть враг, которого мы можем атаковать - берём с минимальным кол-вом хитов
        if len(sorted_visible_enemies) > 0:
            return sorted_visible_enemies[0]

        #иначе берём врага, ближайшего к центру команды
        team_coord = self.team_avg_coord(world)
        nearest_enemies = sorted(enemies, key=lambda e: distance_from_to(team_coord, (e.x, e.y)))

        # todo выбор тех, кто может стрелять в нас всегда приоритетнее, чем те, которые не могут дострелить до команды

        return nearest_enemies[0]

    @staticmethod
    def check_can_kill_unit(me, enemy):
        turn_count = int(floor(me.action_points / me.shoot_cost))
        summary_damage = turn_count * me.get_damage(me.stance)

        return me.action_points >= me.shoot_cost and summary_damage >= enemy.hitpoints

    @staticmethod
    def cell_attack_rank(coord, world):
        return len([t for t in world.troopers if not t.teammate and world.is_visible(t.shooting_range, t.x, t.y,
                                                                                     t.stance, coord[0], coord[1],
                                                                                     TrooperStance.STANDING)])

    def find_path_from_to(self, world, coord_from, coord_to, use_cache=True):
        """
        Ищем кратчайший путь из точки А в точку Б с обходом препятствий и других юнитов
        Если одна из точек непроходима или выходит за пределы поля - отдаём пустой список
        Если в точку финиша ну никак не придти - отдаём пустой список

        :rtype : list of simplest path coords
        """

        log_it('find path call start (%s to %s)' % (str(coord_from), str(coord_to)))

        if coord_from[0] < 0 or coord_from[0] > world.width or coord_from[1] < 0 or coord_from[1] > world.height or \
            coord_to[0] < 0 or coord_to[0] > world.width or coord_to[1] < 0 or coord_to[1] > world.height:

            log_it('invalid point for find_path_from_to %s %s' % (str(coord_from), str(coord_to)), 'error')
            return []

        if coord_from == coord_to:
            return []

        if self.current_path is not None and use_cache:
            try:
                start_index = self.current_path.index(coord_from)
                end_index = self.current_path.index(coord_to)
            except ValueError:
                log_it('get path from cache failed')
            else:
                log_it('cached path found (%s %s)' % (str(start_index), str(end_index)))
                if start_index < end_index:
                    path = self.current_path[start_index+1:end_index]
                else:
                    path = self.current_path[end_index+1:start_index][::-1]
                return path

        # карта проходимости юнитов
        map_passability = [[dict(coord=(x, y), passability=(v == CellType.FREE), wave_num=None)
                            for y, v in enumerate(row)] for x, row in enumerate(world.cells)]

        # отмечаем юнитов в радиусе одного шага как непроходимые препятствия
        short_radius_neibs = [x['coord'] for x in find_cell_neighborhood(coord_from, map_passability)]
        for t in world.troopers:
            try:
                short_radius_neibs.index((t.x, t.y))
                map_passability[t.x][t.y]['passability'] = False
            except ValueError:
                pass

        # Алгоритм Ли для поиска пути из coord_from в coord_to
        map_passability[coord_from[0]][coord_from[1]]['wave_num'] = 0
        map_passability[coord_from[0]][coord_from[1]]['passability'] = True
        last_wave_num = 0

        # обходим волнами все ячейки, ещё не задетые другими волнами
        while True:
            wave_cells = filter_free_wave(map_passability, val=last_wave_num)
            tmp = copy.deepcopy(map_passability)
            last_wave_num += 1
            for cell in wave_cells:
                neighborhoods = find_cell_neighborhood(cell['coord'], map_passability)
                for item in neighborhoods:
                    if item['wave_num'] is None:
                        item['wave_num'] = last_wave_num

            if (len(filter_free_wave(map_passability, val=None)) == 0) or \
                    (map_passability[coord_to[0]][coord_to[1]]['wave_num'] is not None) or \
                    (map_passability == tmp):
                break

        if map_passability[coord_to[0]][coord_to[1]]['wave_num'] is None:
            return []

        end_point = map_passability[coord_to[0]][coord_to[1]]

        # восстанавливаем кратчайший путь до стартовой ячейки
        path = [end_point]
        while True:
            current_cell = path[-1]
            neighborhoods = find_cell_neighborhood(current_cell['coord'], map_passability)
            cells = filter(lambda x: (x['wave_num'] == current_cell['wave_num'] - 1), neighborhoods)
            shuffle(cells)

            new_cell = cells.pop()
            if new_cell['wave_num'] > 0:
                path.append(new_cell)
            else:
                break

        path.reverse()
        out = [i['coord'] for i in path]

        self.current_path = out
        log_it('new path cached')

        log_it('find path call end (%s)' % str(out))
        return out

    @staticmethod
    def _stand_up(move, me, game):
        log_it('start raise stance')
        if me.stance == TrooperStance.STANDING:
            log_it('now max raise stance')
        elif me.action_points < game.stance_change_cost:
            log_it('not enouth AP', 'warn')
        else:
            move.action = ActionType.RAISE_STANCE

    @staticmethod
    def _seat_down(move, me, game):
        log_it('start lower stance')
        if me.stance == TrooperStance.PRONE:
            log_it('now max lower stance')
        elif me.action_points < game.stance_change_cost:
            log_it('not enouth AP', 'warn')
        else:
            move.action = ActionType.LOWER_STANCE

    def _move_to(self, world, move, game, me, coord):
        log_it('start move to %s' % str(coord))

        if me.stance == TrooperStance.STANDING:
            cost = game.standing_move_cost
        elif me.stance == TrooperStance.KNEELING:
            cost = game.kneeling_move_cost
        else:
            cost = game.prone_move_cost

        if me.action_points < cost:
            log_it('not enouth AP', 'warn')
            return

        try:
            cell = world.cells[coord[0]][coord[1]]
        except IndexError:
            log_it('cell not found', 'warn')
        else:
            if not self.cell_free_for_move(coord, world):
                log_it('cell not free')
            else:
                move.action = ActionType.MOVE
                move.x = coord[0]
                move.y = coord[1]

    @staticmethod
    def _eat_ration(move, me, game):
        log_it('start eat ration')
        if me.action_points < game.field_ration_eat_cost:
            log_it('not enouth AP', 'warn')
        else:
            move.action = ActionType.EAT_FIELD_RATION

    @staticmethod
    def _shoot_grenade(move, me, enemy, game):
        log_it('start shoot grenade to %s' % str((enemy.x, enemy.y)))
        if me.action_points < game.grenade_throw_cost:
            log_it('not enouth AP', 'warn')
        else:
            move.action = ActionType.THROW_GRENADE
            move.x = enemy.x
            move.y = enemy.y

    @staticmethod
    def _shoot(move, me, enemy):
        log_it('start shoot to %s' % str((enemy.x, enemy.y)))
        if me.action_points < me.shoot_cost:
            log_it('not enouth AP', 'warn')
        else:
            move.action = ActionType.SHOOT
            move.x = enemy.x
            move.y = enemy.y

    @staticmethod
    def _heal(move, me, enemy, game):
        log_it('start heal to %s' % str((enemy.x, enemy.y)))
        if me.action_points < game.field_medic_heal_cost:
            log_it('not enouth AP', 'warn')
        else:
            move.action = ActionType.HEAL
            move.x = enemy.x
            move.y = enemy.y

    @staticmethod
    def _use_medikit(move, me, enemy, game):
        log_it('start use medikit to %s' % str((enemy.x, enemy.y)))
        if me.action_points < game.medikit_use_cost:
            log_it('not enouth AP', 'warn')
        else:
            move.action = ActionType.USE_MEDIKIT
            move.x = enemy.x
            move.y = enemy.y

    def _lower_stance_or_shoot(self, move, me, enemy, game):
        if me.get_damage(me.stance) * int(floor(me.action_points / me.shoot_cost)) >= enemy.hitpoints:
            self._shoot(move, me, enemy)
        else:
            if me.stance != TrooperStance.PRONE:
                self._seat_down(move, me, game)
            else:
                self._shoot(move, me, enemy)

    def _stand_up_or_move(self, world, move, game, me, coord):
        if me.stance != TrooperStance.STANDING:
            self._stand_up(move, me, game)
        else:
            self._move_to(world, move, game, me, coord)

    def _seat_down_or_move(self, world, move, game, me, coord):
        if me.stance == TrooperStance.STANDING:
            self._seat_down(move, me, game)
        else:
            self._move_to(world, move, game, me, coord)

    def _action_base(self, me, world, game, move):
        self.change_current_waypoint(me)

        # если юнит слишком далеко отошёл от точки базирования отряда - немедленно возвращаться
        if self.max_range_from_team_exceeded(world, me):
            log_it('max range from team coord exceed')

            team_coords = [(t.x, t.y) for t in world.troopers if t.teammate and t.id != me.id]
            coords_to = sorted(team_coords, key=lambda c: me.get_distance_to(*c))[0]

            path = self.find_path_from_to(world, (me.x, me.y), coords_to)
            log_it('path for return to team %s' % str(path), 'debug')
            if len(path) > 0:
                if me.stance != TrooperStance.STANDING:
                    return self._stand_up(move, me, game)
                else:
                    return self._move_to(world, move, game, me, path[0])
        else:
            method = self.select_action_by_type(me.type)
            log_it('select %s action method' % method)
            return getattr(self, method)(me, world, game, move)

    def _action_commander(self, me, world, game, move):
        """
        Держится со всеми.
        Проверяет, нет ли в радиусе досягаемости отряда целей.
        Если нет - встаёт и идёт дальше по направлению.
        Если есть - пытается достичь позиции для атаки
        Если есть аптечка - занимается самолечением (других не лечит - геморно)

        """

        enemy = self.select_enemy(me, world)

        if self.could_and_need_use_medikit(me, me, game):
            log_it('soldier use medikit')
            return self._use_medikit(move, me, me, game)
        elif enemy is not None:
            return self._attack_unit(world, me, move, game, enemy)
        else:
            return self._going_to_waypoint(world, me, move, game)

    def _action_medic(self, me, world, game, move):
        """
        Держится со всеми.
        Пропускает первый ход, чтобы остальные ушли вперёд
        Если остался один - не лечит, а стреляет напоследок
        Если своё здоровье больше лимита - лечит остальных
        Лечит и ходит/мочит как командир.

        """

        heal_enemy = self.select_heal_enemy(me, world)
        team_size = len([t for t in world.troopers if t.teammate])

        if world.move_index == 0:
            log_it('medic pass first turn')
        elif team_size == 1:
            log_it('medic was left alone and move as commander')
            return self._action_commander(me, world, game, move)
        elif heal_enemy is None:
            log_it('medic mode on')
            team_enemies = filter(lambda x: x is not None, [self.select_enemy(t, world) for t in world.troopers
                                                            if t.teammate and t.id != me.id])
            if len(team_enemies) > 0:
                log_it('medic going to team-rear position')
                position = self.select_position_for_medic(me, world)
                log_it('find %s team-rear position' % str(position))
                if position is not None:
                    path = self.find_path_from_to(world, (me.x, me.y), position, False)
                    log_it('path for going to team rear position %s from %s is %s' % (str(position), str((me.x, me.y)),
                                                                                      str(path)), 'debug')
                    if len(path) > 0:
                        return self._stand_up_or_move(world, move, game, me, path[0])
            else:
                return self._going_to_waypoint(world, me, move, game)
        else:
            log_it('medic heal enemy %s' % str(heal_enemy.hitpoints))
            if self.heal_avaliable(me, heal_enemy):
                if self.could_and_need_use_ration(me, game):
                    return self._eat_ration(move, me, game)
                elif self.could_and_need_use_medikit(me, heal_enemy, game):
                    return self._use_medikit(move, me, heal_enemy, game)
                else:
                    return self._heal(move, me, heal_enemy, game)
            else:
                path = self.find_path_from_to(world, (me.x, me.y), (heal_enemy.x, heal_enemy.y))
                log_it('path for going to heal enemy %s from %s is %s' % (str((heal_enemy.x, heal_enemy.y)),
                                                                          str((me.x, me.y)), str(path)), 'debug')
                if len(path) > 0:
                    return self._stand_up_or_move(world, move, game, me, path[0])

    def _going_to_waypoint(self, world, me, move, game):
        nearest_bonus = self.find_bonus(me, world)
        if nearest_bonus is not None:
            log_it('going to bonus %s' % str(nearest_bonus.type))
            path = self.find_path_from_to(world, (me.x, me.y), (nearest_bonus.x, nearest_bonus.y), False)
            log_it('path for going to bonus %s from %s is %s' % (str((nearest_bonus.x, nearest_bonus.y)),
                                                                 str((me.x, me.y)), str(path)), 'debug')
            if len(path) > 0:
                return self._basic_move(path, me, world, move, game)

        log_it('going to waypoint index %s' % str(shared.current_dest_waypoint))
        coord = shared.way_points[shared.current_dest_waypoint]
        path = self.find_path_from_to(world, (me.x, me.y), coord)
        log_it('path for going to waypoint %s from %s is %s' % (str(coord), str((me.x, me.y)), str(path)), 'debug')
        return self._basic_move(path, me, world, move, game)

    def _basic_move(self, path, me, world, move, game):
        if len(path) > 0:
            if self.need_to_wait_medic(me, world):
                log_it('wait a medic')
                return self._seat_down_or_move(world, move, game, me, path[0])
            else:
                log_it('stend up and move')
                return self._stand_up_or_move(world, move, game, me, path[0])

    def _attack_unit(self, world, me, move, game, enemy):
        log_it('attack enemy id %s (hits %s)' % (str(enemy.id), str(enemy.hitpoints)))
        lower_stance = TrooperStance.KNEELING if me.stance == TrooperStance.STANDING else TrooperStance.PRONE
        upper_stance = TrooperStance.KNEELING if me.stance == TrooperStance.PRONE else TrooperStance.STANDING

        if world.is_visible(me.shooting_range, me.x, me.y, me.stance, enemy.x, enemy.y, enemy.stance):
            log_it('attack unit')
            if self.could_and_need_use_ration(me, game):
                return self._eat_ration(move, me, game)
            elif self.could_and_need_use_grenade(me, enemy, game, world):
                return self._shoot_grenade(move, me, enemy, game)
            elif world.is_visible(me.shooting_range, me.x, me.y, lower_stance, enemy.x, enemy.y, enemy.stance):
                return self._lower_stance_or_shoot(move, me, enemy, game)
            else:
                return self._shoot(move, me, enemy)
        elif upper_stance != me.stance and world.is_visible(me.shooting_range, me.x, me.y, TrooperStance.STANDING,
                                                            enemy.x, enemy.y, enemy.stance):
            log_it('raise stance for attack')
            return self._stand_up(move, me, game)
        else:
            log_it('move to unit')
            path = self.find_path_from_to(world, (me.x, me.y), (enemy.x, enemy.y))
            log_it('path for going to enemy %s from %s is %s' % (str((enemy.x, enemy.y)), str((me.x, me.y)),
                                                                 str(path)), 'debug')
            if len(path) > 0:
                return self._seat_down_or_move(world, move, game, me, path[0])


if __name__ == '__main__':
    from Runner import Runner
    Runner().run()
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


# коэф. для вычисления максимальной дальности юнита от точки базирования команды
CF_range_from_team = 0.9

# коэф. для вычисления максимальной дальности юнита от вейпоинта
CF_range_from_waypoint = 0.5

# уровень здоровья врача, при котором он начинает лечить себя первее остальных
CF_medic_heal_level = 0.6


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


def find_cell_neighborhood(coord, map_):
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

    sorted_map = sorted(map_, key=lambda x: x['distance'])

    return sorted_map[0]['coord']


class MyStrategy:

    def __init__(self):
        self.current_path = None
        logging.basicConfig(
            format='%(asctime)s %(levelname)s:%(message)s',
            level=logging.INFO)

    def move(self, me, world, game, move):
        log_it('new move turn %d unit %d (%s)' % (world.move_index, me.id, str((me.x, me.y))))

        if shared.way_points is None:
            self._compute_waypoints(world)

        self._action_base(me, world, game, move)

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

        if len(shared.way_points) > shared.current_dest_waypoint:
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
        if len(ranges_to_team) == 0:
            return False
        else:
            return max(ranges_to_team) > shoot_range * CF_range_from_team

    def need_to_wait_medic(self, me, world):
        return me.type != TrooperType.FIELD_MEDIC and me.hitpoints < me.maximal_hitpoints and \
               len([t for t in world.troopers if t.teammate and t.type == TrooperType.FIELD_MEDIC]) == 1

    def heal_avaliable(self, me, enemy):
        return me.get_distance_to(enemy.x, enemy.y) <= 1.0

    def cell_free_for_move(self, coord, world):
        troopers_coord = [t for t in world.troopers if (t.x, t.y) == coord]
        return world.cells[coord[0]][coord[1]] == CellType.FREE and len(troopers_coord) == 0

    @staticmethod
    def select_heal_enemy(me, world):
        """
        Выбираем союзника для лечения: выбираем ближайшего с неполными хитами

        :rtype Trooper or None
        """

        units_for_heal = [t for t in world.troopers if t.teammate and t.hitpoints < t.maximal_hitpoints]
        if len(units_for_heal) == 0:
            return None

        log_it('find %d units for heal' % len(units_for_heal))
        nearest_units = sorted(units_for_heal, key=lambda u: me.get_distance_to(u.x, u.y))

        # todo оставлять только те цели, до которых можем дойти (либо уже доступных для лечения)

        if nearest_units[0].id == me.id and len(nearest_units) > 1 and \
                (me.hitpoints / me.maximal_hitpoints) >= CF_medic_heal_level:
            log_it('medic select other unit for healing instead of himself %s' % str(me.hitpoints))
            nearest_units.pop(0)

        if len(nearest_units) == 1:
            return nearest_units[0]
        elif len(nearest_units) > 1:
            # todo сравнивать длину пути до юнита вместо гипотенузы
            return nearest_units[0]
        else:
            return None

    def select_enemy(self, me, world):
        """
        Выбираем врага в поле видимости команды
        если в текущем поле досягаемости оружия есть враг и мы можем убить его за оставшиеся ходы - берём его
        иначе ищем врагов в поле видимости команды
            если враги есть - берём ближайшего из них
            иначе - None

        :rtype Trooper or None
        """

        enemies = [t for t in world.troopers if not t.teammate]
        if len(enemies) == 0:
            return None

        # проверяем, нет ли среди ближайших врагов такого, который можно было бы атаковать
        visible_enemies = [e for e in enemies if world.is_visible(me.shooting_range, me.x, me.y, me.stance, e.x, e.y,
                                                                  e.stance)]
        sorted_visible_enemies = sorted(visible_enemies, key=lambda e: e.hitpoints)

        # если в досягаемости есть враг, которого мы можем атаковать - берём с минимальным кол-вом хитов
        if len(sorted_visible_enemies) > 0:
            return sorted_visible_enemies[0]

        #иначе берём врага, ближайшего к центру команды
        team_coord = self.team_avg_coord(world)
        nearest_enemies = sorted(enemies, key=lambda e: distance_from_to(team_coord, (e.x, e.y)))
        return nearest_enemies[0]

    @staticmethod
    def check_can_kill_unit(me, enemy):
        turn_count = int(floor(me.action_points / me.shoot_cost))
        summary_damage = turn_count * me.get_damage(me.stance)

        return me.action_points >= me.shoot_cost and summary_damage >= enemy.hitpoints

    def find_path_from_to(self, world, coord_from, coord_to):
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

        if self.current_path is not None:
            try:
                start_index = self.current_path.index(coord_from)
                end_index = self.current_path.index(coord_to)
            except ValueError:
                log_it('cache path failed')
            else:
                log_it('cache path indexes %s %s' % (str(start_index), str(end_index)))
                return self.current_path[start_index+1:end_index]

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
            log_it('not enouth AP')
        else:
            move.action = ActionType.RAISE_STANCE

    @staticmethod
    def _seat_down(move, me, game):
        log_it('start lower stance')
        if me.stance == TrooperStance.PRONE:
            log_it('now max lower stance')
        elif me.action_points < game.stance_change_cost:
            log_it('not enouth AP')
        else:
            move.action = ActionType.LOWER_STANCE

    def _move_to(self, world, move, game, me, coord):
        log_it('start move to %s' % str(coord))

        if me.stance == TrooperStance.PRONE:
            log_it('not available stance for moving')
            return

        if me.action_points < (game.standing_move_cost if me.stance == TrooperStance.STANDING else game.kneeling_move_cost):
            log_it('not enouth AP')
            return

        try:
            cell = world.cells[coord[0]][coord[1]]
        except IndexError:
            log_it('cell not found')
        else:
            if not self.cell_free_for_move(coord, world):
                log_it('cell not free')
            else:
                move.action = ActionType.MOVE
                move.x = coord[0]
                move.y = coord[1]

    @staticmethod
    def _shoot(move, me, enemy):
        log_it('start shoot to %s' % str((enemy.x, enemy.y)))
        if me.action_points < me.shoot_cost:
            log_it('not enouth AP')
        else:
            move.action = ActionType.SHOOT
            move.x = enemy.x
            move.y = enemy.y

    @staticmethod
    def _heal(move, me, enemy):
        log_it('start heal to %s' % str((enemy.x, enemy.y)))
        if me.action_points < me.shoot_cost:
            log_it('not enouth AP')
        else:
            move.action = ActionType.HEAL
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
            log_it('path for return to team %s' % str(path))
            if len(path) > 0:
                if me.stance != TrooperStance.STANDING:
                    self._stand_up(move, me, game)
                else:
                    self._move_to(world, move, game, me, path[0])
        else:
            method = self.select_action_by_type(me.type)
            log_it('select %s action method' % method)
            getattr(self, method)(me, world, game, move)

    def _action_commander(self, me, world, game, move):
        """
        Держится со всеми.
        Проверяет, нет ли в радиусе досягаемости отряда целей.
        Если нет - встаёт и идёт дальше по направлению.
        Если есть - пытается достичь позиции для атаки

        """

        enemy = self.select_enemy(me, world)
        if enemy is not None:
            log_it('find enemy for attack %s' % str(enemy.id))

            lower_stance = TrooperStance.KNEELING if me.stance == TrooperStance.STANDING else TrooperStance.PRONE
            if world.is_visible(me.shooting_range, me.x, me.y, me.stance, enemy.x, enemy.y, enemy.stance):
                if world.is_visible(me.shooting_range, me.x, me.y, lower_stance, enemy.x, enemy.y, enemy.stance):
                    self._lower_stance_or_shoot(move, me, enemy, game)
                else:
                    self._shoot(move, me, enemy)
            else:
                path = self.find_path_from_to(world, (me.x, me.y), (enemy.x, enemy.y))
                log_it('path for going to enemy %s from %s is %s' % (str((enemy.x, enemy.y)), str((me.x, me.y)),
                                                                     str(path)))
                if len(path) > 0:
                    self._stand_up_or_move(world, move, game, me, path[0])
        else:
            coord = shared.way_points[shared.current_dest_waypoint]
            path = self.find_path_from_to(world, (me.x, me.y), coord)
            log_it('path for going to waypoint %s from %s is %s' % (str(coord), str((me.x, me.y)), str(path)))
            if len(path) > 0:
                if self.need_to_wait_medic(me, world):
                    log_it('wait a medic')
                    self._seat_down_or_move(world, move, game, me, path[0])
                else:
                    self._stand_up_or_move(world, move, game, me, path[0])

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
            self._action_commander(me, world, game, move)
        elif heal_enemy is None:
            log_it('medic move as commander')
            self._action_commander(me, world, game, move)
        else:
            log_it('medic heal enemy %s' % str(heal_enemy.id))
            if self.heal_avaliable(me, heal_enemy):
                self._heal(move, me, heal_enemy)
            else:
                path = self.find_path_from_to(world, (me.x, me.y), (heal_enemy.x, heal_enemy.y))
                log_it('path for going to heal enemy %s from %s is %s' % (str((heal_enemy.x, heal_enemy.y)),
                                                                          str((me.x, me.y)), str(path)))
                if len(path) > 0:
                    self._stand_up_or_move(world, move, game, me, path[0])



if __name__ == '__main__':
    from Runner import Runner
    Runner().run()
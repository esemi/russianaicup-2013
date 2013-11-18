#! /usr/bin/env python
# -*- coding: utf-8 -*-


import logging

import copy
from math import *
from random import shuffle

from model.ActionType import ActionType
from model.TrooperStance import TrooperStance
from model.TrooperType import TrooperType
from model.CellType import CellType


# коэф., на который домножается средний радиус стрельбы отряда при вычислении дальности юнита от точки базирования команды
CF_range_from_team = 1.0


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


class MyStrategy:

    def __init__(self):
        self.way_points = None
        self.dest_way_point_index = None
        logging.basicConfig(
            format='%(asctime)s %(levelname)s:%(message)s',
            level=logging.INFO)

    def move(self, me, world, game, move):
        log_it('new move turn %d' % world.move_index)

        # на первом ходу никто не двигается, для вычисления реперных точек
        if self.way_points is None:
            log_it('first turn - init waypoints')
            self._compute_waypoints(world)
        else:
            self._action_base(me, world, game, move)

    @property
    def dest_way_point_index(self):
        return self._dest_way_point_index

    @dest_way_point_index.setter
    def dest_way_point_index(self, value):
        self._dest_way_point_index = value

    @property
    def way_points(self):
        return self._way_points

    @way_points.setter
    def way_points(self, value):
        self._way_points = value

    @staticmethod
    def select_action_by_type(type_):
        if type_ == TrooperType.COMMANDER:
            return '_action_commander'
        elif type_ == TrooperType.FIELD_MEDIC:
            return '_action_medic'
        elif type_ == TrooperType.SOLDIER:
            return '_action_soldier'
        elif type_ == TrooperType.SNIPER:
            return '_action_sniper'
        elif type_ == TrooperType.SCOUT:
            return '_action_scout'
        else:
            raise ValueError("Unsupported unit type: %s." % type_)

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

        """
        # todo оставлять только досягаемые вейкпоинты

        current_coord = self.team_avg_coord(world)
        log_it("compute current command coord %s" % str(current_coord))

        center_coord = (int(world.width / 2), int(world.height / 2))

        angles = [
            (0, 0),
            (0, world.height - 1),
            (world.width - 1, world.height - 1),
            (world.width - 1, 0)]

        sorted_waypoints = []
        for k in xrange(len(angles)):
            if k == 0:
                angles = sorted(angles, key=lambda i: distance_from_to(current_coord, i))
            else:
                angles = sorted(angles, key=lambda i: distance_from_to(sorted_waypoints[k-1], i))
            sorted_waypoints.append(angles.pop(0))

        sorted_waypoints.append(center_coord)
        self.way_points = sorted_waypoints
        log_it('select %s waypoints' % str(sorted_waypoints))

    def _change_current_waypoint(self, me):
        """
        Если юнит достиг видимости вейпоинта - выбирает следующий вейпоинт
        Если вейпоинт ещё не задан - берёт первый из списка
        Если достигнут последний вейпоинт - удерживаем позицию (каждый солдат сам решает как лучше удерживать)
        """

        log_it("current dest waypoint is %s" % str(self.dest_way_point_index))

        if self.dest_way_point_index is None:
            self.dest_way_point_index = 0

        distance_to_waypoint = me.get_distance_to(*self.way_points[self.dest_way_point_index])
        log_it('distance to waypoint %s (range %s)' % (distance_to_waypoint, me.vision_range))

        if distance_to_waypoint < me.vision_range and len(self.way_points) > self.dest_way_point_index:
            self.dest_way_point_index += 1
            log_it("new dest waypoint is %s" % str(self.dest_way_point_index))

    def max_range_from_team_exceeded(self, world, me):
        """
        Проверяем - не ушёл ли юнит на максимальную дальность от отряда:
        слишком далеко = средняя дальность обстрела отряда * CF_range_from_team

        """

        team_coord = self.team_avg_coord(world)
        shoot_range = self.team_avg_shooting_range(world)
        return me.get_distance_to(*team_coord) > shoot_range * CF_range_from_team

    def select_enemy(self, me, world):
        """
        Выбираем врага в поле видимости команды
        если в текущем поле досягаемости оружия есть враг и мы можем убить его за оставшиеся ходя - берём его
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

        # если в досягаемости есть враг, которого мы сможем убить за оставшиеся ходы - вернём его
        if len(sorted_visible_enemies) > 0 and self.check_can_kill_unit(me, sorted_visible_enemies[0]):
            return sorted_visible_enemies[0]

        # берём врага, ближайшего к центру команды
        team_coord = self.team_avg_coord(world)
        nearest_enemies = sorted(enemies, key=lambda e: distance_from_to(team_coord, (e.x, e.y)))
        return nearest_enemies[0]

    @staticmethod
    def check_can_kill_unit(me, enemy):
        turn_count = int(floor(me.action_points / me.shoot_cost))
        summary_damage = turn_count * me.get_damage(me.stance)

        return me.action_points >= me.shoot_cost and summary_damage >= enemy.hitpoints

    @staticmethod
    def find_path_from_to(world, coord_from, coord_to):
        """
        Ищем кратчайший путь из точки А в точку Б с обходом препятствий и других юнитов
        Если одна из точек непроходима или выходит за пределы поля - отдаём пустой список
        Если в точку финиша ну никак не придти - отдаём пустой список

        :rtype : list of simplest path coords
        """

        if coord_from[0] < 0 or coord_from[0] > world.width or coord_from[1] < 0 or coord_from[1] > world.height or \
                        coord_to[0] < 0 or coord_to[0] > world.width or coord_to[1] < 0 or coord_to[1] > world.height:
            log_it('invalid point for find_path_from_to %s %s' % (str(coord_from), str(coord_to)), 'error')
            return []

        # карта проходимости юнитов
        map_passability = [[dict(coord=(x, y), passability=(v == CellType.FREE), wave_num=None)
                            for y, v in enumerate(row)] for x, row in enumerate(world.cells)]

        # отмечаем юнитов в радиусе одного шага как непроходимые препятствия
        short_radius_neibs = [x['coord'] for x in find_cell_neighborhood(coord_from, map_passability)]
        for t in world.troopers:
            try:
                short_radius_neibs.index((t.x, t.y))
                map_passability[t.x][t.y]['passability'] = False
                log_it('%s check as unpassability' % str((t.x, t.y)))
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

            # будем надеяться, что конечная точка не окажется в замкнутой области, ибо тогда цикл будет бесконечен)
            if (len(filter_free_wave(map_passability, val=None)) == 0) or \
                    (map_passability[coord_to[0]][coord_to[1]]['wave_num'] is not None) or \
                    (map_passability == tmp):
                break

        if map_passability[coord_to[0]][coord_to[1]]['wave_num'] is None:
            return []  # todo приспосаблиываться к финишной точке, к которой не дойти

        end_point = map_passability[coord_to[0]][coord_to[1]]

        # восстанавливаем кратчайший путь до стартовой ячейки от выбранной конечной (может быть не финишная, а ближайшая к ней)
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
        return [i['coord'] for  i in path]

    @staticmethod
    def _stend_up(move, me, game):
        log_it('start raise stance to %s')
        if me.action_points < game.stance_change_cost:
            log_it('not enouth AP')
        else:
            move.action = ActionType.RAISE_STANCE

    @staticmethod
    def _move_to(world, move, game, me, coord):
        log_it('start move to %s' % str(coord))
        if me.action_points < game.stance_change_cost:
            log_it('not enouth AP')
            return

        try:
            if world.cells[coord[0]][coord[1]] != CellType.FREE:
                log_it('cell not free')
                return
        except IndexError:
            log_it('cell not found')
            return

        move.action = ActionType.MOVE
        move.x = coord[0]
        move.y = coord[1]

    def _action_base(self, me, world, game, move):
        self._change_current_waypoint(me)

        # если юнит слишком далеко отошёл от точки базирования отряда - немедленно возвращаться
        if self.max_range_from_team_exceeded(world, me):
            log_it('max range from team coord exceed')
            path = self.find_path_from_to(world, (me.x, me.y), self.team_avg_coord(world))
            log_it('path for return to team %s' % str(path))
            if len(path) > 0:
                if me.stance != TrooperStance.STANDING:
                    self._stend_up(move, me, game)
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
        Если есть - пытается достичь позиции для атаки, пробует присесть и мочить.

        """

        enemy = self.select_enemy(me, world)
        if enemy is not None:
            log_it('find enemy for attack %s' % str(enemy))
            # todo release
        else:
            coord = self.way_points[self.dest_way_point_index]
            path = self.find_path_from_to(world, (me.x, me.y), coord)
            log_it('path for going to waypoint %s from %s is %s' % (str(coord), str((me.x, me.y)), str(path)))
            if len(path) > 0:
                if me.stance != TrooperStance.STANDING:
                    self._stend_up(move, me, game)
                else:
                    self._move_to(world, move, game, me, path[0])

    def _action_medic(self, me, world, game, move):
        """
        Держится со всеми.
        Лечит и ходит/мочит как командир.

        """
        #todo release
        self._action_commander(me, world, game, move)

    def _action_soldier(self, me, world, game, move):
        """
        Держится со всеми.
        Ходит мочит как командир.

        """

        self._action_commander(me, world, game, move)

    def _action_sniper(self, me, world, game, move):
        """
        Держится со всеми.
        Ходит мочит как командир.

        """

        self._action_commander(me, world, game, move)

    def _action_scout(self, me, world, game, move):
        """
        Держится со всеми.
        Ходит мочит как командир.

        """

        self._action_commander(me, world, game, move)


if __name__ == '__main__':
    from Runner import Runner
    Runner().run()
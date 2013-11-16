#! /usr/bin/env python
# -*- coding: utf-8 -*-


import logging

from model.TrooperType import TrooperType
from math import *


# коэф., на который домножается средний радиус стрельбы отряда при вычислении дальности юнита от точки базирования команды
CF_range_from_team = 1.5


def log_it(msg, level='info'):
    getattr(logging, level)(msg)


def distance_from_to(coord_from, coord_to):
    return hypot(coord_to[0] - coord_from[0], coord_to[1] - coord_from[1])


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
        return round(sum(current_x) / len(current_x)), round(sum(current_y) / len(current_y))

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

        current_coord = self.team_avg_coord(world)
        log_it("compute current command coord %s" % str(current_coord))

        center_coord = (round(world.width / 2), round(world.height / 2))

        angles = [
            (0, 0),
            (0, world.height),
            (world.width, world.height),
            (world.width, 0),
        ]

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
        else:
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

    @staticmethod
    def find_path_from_to(world, coord_from, coord_to):
        """
        Ищем кратчайшиу путь из точки А в точку Б с обходом препятствий

        :rtype : list of path coords
        """
        return []

    def _action_base(self, me, world, game, move):
        self._change_current_waypoint(me)

        # если юнит слишком далеко отошёл от точки базирования отряда - немедленно возвращаться
        if self.max_range_from_team_exceeded(world, me):
            log_it('max range from team coord exceed')
            path = self.find_path_from_to(world, me, self.team_avg_coord(world))
            log_it('path for return to team %s' % str(path))
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
        pass

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
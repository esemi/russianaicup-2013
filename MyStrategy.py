#! /usr/bin/env python
# -*- coding: utf-8 -*-


import logging

from model.TrooperType import TrooperType
from math import *


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

        if me.action_points < game.standing_move_cost:
            log_it('end turn (%d/%d)' % (me.action_points, game.standing_move_cost))
            return

        # на первом ходу никто не двигается, для вычисления реперных точек
        if self.way_points is None:
            log_it('first turn - init waypoints')
            self._compute_waypoints(world, me)
            return

        method = self._select_action_by_type(me.type)
        log_it('select %s action method' % method)

        self._action_base(me, world, game, move)
        getattr(self, method)(me, world, game, move)

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

    def _compute_waypoints(self, world, me):

        # вычисляем координаты точки базирования отряда (среднее значение координат)
        current_x = [t.x for t in world.troopers if t.teammate]
        current_y = [t.y for t in world.troopers if t.teammate]
        current_coord = (sum(current_x) / len(current_x), sum(current_y) / len(current_y))
        log_it("compute current command coord %s" % str(current_coord))

        center_coord = (round(world.width / 2), round(world.height / 2))

        waypoints = [
            (0, 0),
            (0, world.height),
            (world.width, world.height),
            (world.width, 0),
        ]

        sorted_waypoints = []
        for k in xrange(len(waypoints)):
            point_for_sort = waypoints[k:]
            if k == 0:
                tmp = sorted(point_for_sort, key=lambda i: distance_from_to(current_coord, i))
            else:
                tmp = sorted(point_for_sort, key=lambda i: distance_from_to(sorted_waypoints[k-1], i))

            log_it('TEST %d %s %s' % (k, str(tmp), str(point_for_sort)))
            sorted_waypoints.append(tmp[0])

        print sorted_waypoints

        sorted_waypoints.append(center_coord)
        self.way_points = sorted_waypoints
        log_it('select %s waypoints' % str(sorted_waypoints))

    def _action_commander(self, me, world, game, move):
        """
        Держится со всеми.
        Проверяет, нет ли в радиусе досягаемости отряда целей.
        Если нет - встаёт и идёт дальше по направлению.
        Если есть - пытается достичь позиции для атаки и пробует присесть и мочить.
        """
        pass

    def _action_medic(self, me, world, game, move):
        """
        Держится сзади.
        Лечит и ходит/мочит как командир.
        """
        pass

    def _action_soldier(self, me, world, game, move):
        """
        Держится со всеми.
        Ходит мочит как командир.
        """
        pass

    def _action_sniper(self, me, world, game, move):
        """
        Держится со всеми.
        Ходит мочит как командир.
        """
        pass

    def _action_scout(self, me, world, game, move):
        """
        Держится впереди.
        Ходит мочит как командир.
        """
        pass

    def _select_action_by_type(self, type_):
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

    def _action_base(self, me, world, game, move):
        """
        Если юнит достиг видимости вейпоинта - выбирает следующий вейпоинт
        Если вейпоинт ещё не задан - берёт первый из списка
        Если достигнут последний вейпоинт - удерживаем позицию (каждый солдат сам решает как лучше удерживать)
        """

        log_it('action base select waypoint')
        log_it("current dest waypoint is %s %s" % (str(self.dest_way_point_index), str(self.way_points)))

        if self.dest_way_point_index is None:
            self.dest_way_point_index = 0
        else:
            distance_to_waypoint = me.get_distance_to(*self.way_points[self.dest_way_point_index])
            log_it('distance to waypoint %s (range %s)' % (distance_to_waypoint, me.vision_range))

            if distance_to_waypoint < me.vision_range and len(self.way_points) > self.dest_way_point_index:
                self.dest_way_point_index += 1

        log_it("current dest waypoint is %s %s" % (str(self.dest_way_point_index), str(self.way_points)))


if __name__ == '__main__':
    from Runner import Runner
    Runner().run()
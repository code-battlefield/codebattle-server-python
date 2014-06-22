# -*- coding: utf-8 -*-

__author__ = 'Wang Chao'
__date__ = '14-6-22'

import random
import time
import logging

from codebattle import message

logger = logging.getLogger('codebattle.marine')

GUNSHOT_INTERVAL = 2

class MarineGunCoolDown(Exception):
    pass

class MarineEmptyFlares(Exception):
    pass

class MarineOutOfMap(Exception):
    pass


class Marine(object):
    GunCoolDown = MarineGunCoolDown
    EmptyFlares = MarineEmptyFlares
    OutOfMap = MarineOutOfMap

    def __init__(self, id, position):
        self.id = id
        self.hp = 100
        self.position = position
        self.status = message.marine_pb2.Idle
        self.target_position = [0, 0]
        self.role = message.marine_pb2.Normal
        self.flares_amount = 10
        self.last_gunshot_time = 0
        self.player = None

        logger.debug("Create Marine {0}".format(self.id))


    def set_player(self, player):
        """

        :param player: codebattle.player.Player
        """
        self.player = player

    @property
    def died(self):
        return self.hp <= 0

    def can_gunshot(self):
        if int(time.time()) - self.last_gunshot_time < GUNSHOT_INTERVAL:
            return False
        return True

    def can_flare(self):
        return self.flares_amount > 0


    def check_position(self, position):
        x, z = position.x, position.z
        map_x, map_z = self.player.room.terrain.size
        if x < 0 or x > map_x or z < 0 or z > map_z:
            raise self.OutOfMap()

    def set_target_position(self, position):
        if not position:
            return

        self.check_position(position)
        self.target_position = [position.x, position.z]


    def set_position(self, position):
        self.check_position(position)
        self.position = [position.x, position.z]


    def set_status(self, new_status, target_position=None):
        if new_status == message.marine_pb2.GunAttack:
            if not self.can_gunshot():
                raise self.GunCoolDown()

            self.set_target_position(target_position)
            self.status = new_status
            return

        if new_status == message.marine_pb2.Flares:
            if not self.can_flare():
                raise self.EmptyFlares()

            self.status = new_status
            self.flares_amount -= 1
            return

        self.set_target_position(target_position)
        self.status = new_status


    def set_role(self, new_role):
        self.role = new_role

    def got_damaged(self):
        self.hp -= 10
        logger.debug("Marine Got Damage. New Hp {0}".format(self.hp))


    def update(self, status, position=None, target_position=None, role=message.marine_pb2.Normal, damaged=False):
        self.set_status(status, target_position)
        if position:
            self.set_position(position)

        self.set_role(role)
        if damaged:
            self.got_damaged()




class MarineFactory(object):
    @staticmethod
    def create_marines(map_size, amount, keeped_ids=None):
        ids = []
        keeped_ids = keeped_ids or []
        while len(ids) < amount:
            random_id = random.randint(1, 999999)
            if random_id not in keeped_ids and random_id not in ids:
                ids.append(random_id)

        marines = []
        for _id in ids:
            position = [random.randint(1, map_size[0]), random.randint(1, map_size[1])]
            m = Marine(_id, position)
            marines.append(m)

        return marines

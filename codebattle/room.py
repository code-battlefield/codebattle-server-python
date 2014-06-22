# -*- coding: utf-8 -*-

__author__ = 'Wang Chao'
__date__ = '14-6-22'

import random
import logging

import gevent
from gevent.event import Event

from codebattle.terrain import Terrain
from codebattle import message


logger_room = logging.getLogger('codebattle.room')
logger_room_mamager = logging.getLogger('codebattle.roomManager')


class Room(gevent.Greenlet):
    def __init__(self, room_id, terrain, max_players, max_seconds):
        self.id = room_id
        self.terrain = terrain
        self.max_players = max_players
        self.observers = []
        self.alive_players = []
        self.died_players = []
        self.battle_stared = False
        self.battle_timeout = False
        self.battle_start_event = Event()
        self.battle_finish_event = Event()

        gevent.Greenlet.__init__(self)

        self.jobs = []
        job_guard = gevent.spawn(self.guard_max_seconds, max_seconds)
        self.jobs.append(job_guard)

        logger_room.info("Create Room {0}".format(self.id))


    def guard_max_seconds(self, max_seconds):
        gevent.sleep(max_seconds)
        self.battle_timeout = True
        logger_room.info("Room {0} Timeout in seconds {1}.".format(self.id, max_seconds))
        self.battle_start_event.set()
        self.battle_finish_event.set()


    def player_join(self, player):
        """

        :param player: codebattle.player.Player
        :return: Boolean
        """
        if self.battle_stared:
            return False
        if len(self.alive_players) >= self.max_players:
            return False

        player.set_room(self)
        player.link(self.player_died)
        self.alive_players.append(player)

        logger_room.info("Player {0} join room {1}".format(id(player), self.id))

        if len(self.alive_players) == self.max_players:
            self.battle_start_event.set()

        return True


    def player_died(self, player):
        """

        :param player: codebattle.player.Player
        """
        player.unlink(self.player_died)
        self.alive_players.remove(player)
        self.died_players.append(player)
        self.battle_finish_event.set()


    def observer_join(self, ob):
        """

        :param ob: codebattle.observer.Observer
        :return: Boolean
        """
        ob.set_room(self)
        self.observers.append(ob)
        logger_room.info("Observer join")
        return True


    def battle_start(self):
        if self.battle_stared:
            return

        self.battle_start_event.wait()
        self.battle_stared = True
        for p in self.alive_players:
            p.put_data(message.player.pack_start_battle_message())

        logger_room.info("Battle Started")


    def battle_finish(self):
        self.battle_finish_event.wait()
        if self.battle_timeout:
            reason = "Timeout"
        else:
            reason = "Normal"

        logger_room.info("Battle Finished. {0}".format(reason))
        for p in self.alive_players:
            p.battle_win = True
            p.endbattle(reason)
        for p in self.died_players:
            p.battle_win = False
            p.endbattle(reason)

        gevent.sleep(0.1)
        for p in self.observers:
            p.terminate()

        for p in self.alive_players:
            p.terminate()

        for p in self.died_players:
            p.terminate()


    def broadcast_to_all(self, data):
        self.broadcast_to_observers(data)
        self.broadcast_to_players(data)


    def broadcast_to_observers(self, data, exclude=None):
        for p in self.observers:
            if p == exclude:
                continue
            p.put_data(data)

    def broadcast_to_players(self, data, exclude=None):
        for p in self.alive_players:
            if p == exclude:
                continue
            p.put_data(data)


    def notify_players(self, data):
        for p in self.alive_players:
            p.notify(data)


    def report_idle(self, marine, caller):
        caller.put_data(message.player.pack_sence_update_message([marine], []))


    def report_damage(self, marine, caller):
        self.broadcast_to_observers(message.observer.pack_sence_update_message(marine))
        caller.put_data(message.player.pack_sence_update_message([marine], []))
        data = message.player.pack_sence_update_message([], [marine])
        self.broadcast_to_players(data, exclude=caller)


    def report_flares(self, marine, caller, flares2=False):
        gevent.sleep(0.01)
        other_players = [p for p in self.alive_players if p != caller]
        other_marines = []
        for p in other_players:
            other_marines.extend(p.get_alive_marines())

        caller.put_data(message.player.pack_sence_update_message([marine], other_marines))

        if not flares2:
            data = message.player.pack_sence_update_message([], [marine])
            for p in other_players:
                p.put_data(data)


    def report_gunattack(self, marine, caller):
        other_players = [p for p in self.alive_players if p != caller]

        data = message.player.pack_sence_update_message([], [marine])
        for p in other_players:
            p.put_data(data)


    def _run(self):
        self.battle_start()
        self.battle_finish()
        gevent.killall(self.jobs)
        logger_room.info("Room {0} finish".format(self.id))



class RoomManager(object):
    rooms = {}

    class RoomNotFound(Exception):
        pass

    class RoomFull(Exception):
        pass

    @classmethod
    def log_room_ids(cls):
        logger_room_mamager.debug("Room Ids {0}".format(cls.rooms.keys()))


    @classmethod
    def generate_room_id(cls):
        while True:
            _id = random.randint(1000000, 9999999)
            if _id not in cls.rooms:
                return _id


    @classmethod
    def create_room(cls, map_id, max_player, max_seconds):
        terrain = Terrain(map_id)

        _id = cls.generate_room_id()
        room = Room(_id, terrain, max_player, max_seconds)
        room.start()

        room.link(cls.destroy_room)
        cls.rooms[_id] = room

        cls.log_room_ids()
        return room


    @classmethod
    def destroy_room(cls, room):
        cls.rooms.pop(room.id)
        cls.log_room_ids()


    @classmethod
    def get_room(cls, _id):
        try:
            return cls.rooms[_id]
        except KeyError:
            logger_room_mamager.warning("Try to get a NONE exist room. Id: {0}".format(_id))
            cls.log_room_ids()
            raise cls.RoomNotFound()


    @classmethod
    def observer_join_room(cls, _id, observer):
        """

        :param _id: Int
        :param observer: codebattle.observer.Observer
        :return: raise cls.RoomNotFound: Boolean
        """
        room = cls.get_room(_id)
        return room.observer_join(observer)


    @classmethod
    def player_join_room(cls, _id, player):
        """

        :param _id: Int
        :param player: codebattle.player.Player
        :return: :raise cls.RoomFull: raise cls.RoomNotFound: codebattle.room.Room
        """
        room = cls.get_room(_id)
        joined = room.player_join(player)
        if not joined:
            raise cls.RoomFull()

        return room

# -*- coding: utf-8 -*-

__author__ = 'Wang Chao'
__date__ = '14-6-22'

import gevent
from gevent.queue import Queue
from gevent.event import Event
from gevent.server import StreamServer

import logging

from codebattle.endpoint import EndPoint
from codebattle.room import RoomManager
from codebattle.marine import MarineFactory, Marine
from codebattle import message

logger = logging.getLogger('codebattle.player')
PLAYER_MARINE_AMOUNT = 2


class Player(EndPoint):
    def __init__(self, transport):
        super(Player, self).__init__(transport)
        self.alive_marines = {}
        self.died_marines = {}
        self.battle_win = False
        self.battle_finish_event = Event()
        self.notify_queue = Queue()


    def get_alive_marines(self):
        return self.alive_marines.values()


    def notify(self, data):
        self.notify_queue.put(data)


    def get_notified(self):
        while True:
            data = self.notify_queue.get()
            if data.report == message.observer_pb2.toidle:
                if data.midle.id not in self.alive_marines:
                    continue

                this_marine = self.alive_marines[data.midle.id]
                this_marine.update(data.report, data.midle.position)
                self.room.report_idle(this_marine, self)
                continue


            if data.report == message.observer_pb2.damage:
                if data.mdamage.id in self.alive_marines:
                    # own marine has been attacked
                    this_marine = self.alive_marines[data.mdamage.id]
                    this_marine.update(data.mdamage.status, position=data.mdamage.position, role=message.marine_pb2.Injured, damaged=True)

                    if this_marine.died:
                        self.marine_die(this_marine)

                    self.room.report_damage(this_marine, self)
                    continue

                if data.mattack.id in self.alive_marines:
                    this_marine = self.alive_marines[data.mattack.id]
                    this_marine.update(data.mattack.status, position=data.mattack.position, role=message.marine_pb2.Attacker)
                    self.room.report_damage(this_marine, self)
                    continue


            if data.report == message.observer_pb2.flares or data.report == message.observer_pb2.flares2:
                for m in data.marines:
                    if m.id in self.alive_marines:
                        self.alive_marines[m.id].update(m.status, position=m.position)

                if data.reporterId in self.alive_marines:
                    self.room.report_flares(self.alive_marines[data.reporterId], self, data.report==message.observer_pb2.flares2)

                continue

            if data.report == message.observer_pb2.gunattack:
                for m in data.marines:
                    if m.id in self.alive_marines:
                        self.alive_marines[m.id].update(m.status, m.position)

                if data.reporterId in self.alive_marines:
                    self.room.report_gunattack(self.alive_marines[data.reporterId], self)


    def marine_batch_add(self, marines, color):
        for m in marines:
            self.alive_marines[m.id] = m
            m.set_player(self)

        logger.debug("Player {0} alive marines {1}".format(id(self), self.alive_marines.keys()))
        self.room.broadcast_to_observers(message.observer.pack_create_marine_message(marines, color))


    def marine_die(self, m):
        logger.info("Player {0}. Marine {1} Died".format(id(self), m.id))
        m.update(status=message.marine_pb2.Dead)
        self.alive_marines.pop(m.id)
        self.died_marines[m.id] = m

        if not self.alive_marines:
            self.room.player_died(self)

    def on_connection_closed(self):
        logger.info("Player {0} closed the connection".format(id(self)))

    def on_connection_lost(self):
        logger.info("Player {0} lost".format(id(self)))


    def on_data(self, data):
        cmd, data = message.player.unpack(data)
        if cmd == message.PLAYER_JOIN_ROOM:
            try:
                room = RoomManager.player_join_room(data.roomid, self)
            except RoomManager.RoomNotFound:
                logger.warning("Player {0} Try to join a NONE exist room {1}".format(id(self), data.roomid))
                self.put_data(message.player.pack_join_room_error_response(14))
                return
            except RoomManager.RoomFull:
                logger.warning("Player {0} Try to join a FULL room {1}".format(id(self), data.roomid))
                self.put_data(message.player.pack_join_room_error_response(15))
                return

            marines = MarineFactory.create_marines(room.terrain.size, PLAYER_MARINE_AMOUNT)
            self.marine_batch_add(marines, data.color)
            self.put_data(message.player.pack_join_room_response(room.id, room.terrain.size, marines))
            return

        if cmd == message.PLAYER_CREATE_MARINE:
            raise NotImplementedError("Player Create Marine Not Implemented")

        if cmd == message.PLAYER_OPERATE_MARINE:
            self.marine_operate(data.id, data.status, data.targetPostion)


    def marine_operate(self, _id, status, position=None):
        if not self.room.started:
            logger.warning("Player {0} operate marine before battle start".format(id(self)))
            self.put_data(message.player.pack_operate_marine_response(25))
            return

        if _id in self.died_marines:
            logger.warning("Player {0} Try to operate a died marine {1}".format(id(self), _id))
            self.put_data(message.player.pack_operate_marine_response(21))
            return

        try:
            marine = self.alive_marines[_id]
        except KeyError:
            logger.warning("Player {0} Try to operate a NONE exist marine {1}".format(id(self), _id))
            self.put_data(message.player.pack_operate_marine_response(20))
            return

        try:
            marine.update(status, target_position=position)
        except Marine.GunCoolDown:
            self.put_data(message.player.pack_operate_marine_response(22))
            return
        except Marine.EmptyFlares:
            self.put_data(message.player.pack_operate_marine_response(23))
            return
        except Marine.OutOfMap:
            self.put_data(message.player.pack_operate_marine_response(24))
            return

        self.room.broadcast_to_observers(message.observer.pack_sence_update_message(marine))


    def endbattle(self, reason):
        self.put_data(message.player.pack_end_battle_message(reason, self.battle_win))
        self.battle_finish_event.set()


    def _run(self):
        super(Player, self)._run()
        job = gevent.spawn(self.get_notified)
        self.battle_finish_event.wait()
        job.kill()
        logger.info("Player {0} finish...".format(id(self)))



class PlayerManager(gevent.Greenlet):
    def __init__(self, port):
        self.port = port
        gevent.Greenlet.__init__(self)

    def _connection_handler(self, client, address):
        logger.info("New Connection From {0}".format(address))
        player = Player(client)
        player.start()


    def _run(self):
        logger.info("Player Listen at port {0}".format(self.port))
        server = StreamServer(('0.0.0.0', self.port), self._connection_handler)
        server.serve_forever()

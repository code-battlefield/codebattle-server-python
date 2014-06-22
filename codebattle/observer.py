# -*- coding: utf-8 -*-

__author__ = 'Wang Chao'
__date__ = '14-6-22'

import gevent
from gevent.server import StreamServer

import logging

from codebattle.endpoint import EndPoint
from codebattle.room import RoomManager
from codebattle import message


logger = logging.getLogger('codebattle.observer')

MAX_PLAYERS = 2
MAX_SECONDS = 60 * 10

class Observer(EndPoint):
    def on_connection_closed(self):
        logger.info("Observer {0} closed the connecton".format(id(self)))

    def on_connection_lost(self):
        logger.warning("Observer {0} lost".format(id(self)))

    def on_data(self, data):
        cmd, data = message.observer.unpack(data)
        if cmd == message.OBSERVER_CREATE_ROOM:
            # TODO a observer only can create one room
            room = RoomManager.create_room(data.map, MAX_PLAYERS, MAX_SECONDS)
            RoomManager.observer_join_room(room.id, self)

            msg = message.observer.pack_create_room_message(0, room.id, room.terrain.size)
            self.put_data(msg)
            return

        if cmd == message.OBSERVER_JOIN_ROOM:
            raise NotImplementedError("Observer Join Room Not Implemented")

        if cmd == message.OBSERVER_MARINE_REPORT:
            self.room.notify_players(data)
            return



class ObserverManager(gevent.Greenlet):
    def __init__(self, port):
        self.port = port
        gevent.Greenlet.__init__(self)


    def _connection_handler(self, client, address):
        logger.info("New Connection From {0}".format(address))
        observer = Observer(client)
        observer.start()


    def _run(self):
        logger.info("Observer Listen at port {0}".format(self.port))
        server = StreamServer(('0.0.0.0', self.port), self._connection_handler)
        server.serve_forever()

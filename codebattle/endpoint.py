# -*- coding: utf-8 -*-

__author__ = 'Wang Chao'
__date__ = '14-6-22'


import gevent
from gevent.queue import Queue

import struct


class EndPoint(gevent.Greenlet):
    def __init__(self, transport):
        self.transport = transport
        self.header_fmt = struct.Struct('>i')
        self.inbox = Queue()
        self.room = None
        self.jobs = []

        gevent.Greenlet.__init__(self)


    def put_data(self, data):
        self.inbox.put(data)


    def set_room(self, room):
        """

        :param room: codebattle.room.Room
        """
        self.room = room


    def recv_data(self):
        while True:
            try:
                length = self.transport.recv(4)
                if not length:
                    self.on_connection_closed()
                    break

                length = self.header_fmt.unpack(length)[0]
                data = self.transport.recv(length)
            except:
                self.on_connection_lost()
                break

            self.on_data(data)


    def send_data(self):
        while True:
            data = self.inbox.get()
            data_length = len(data)
            fmt = '>i%ds' % data_length
            data_struct = struct.Struct(fmt)
            data = data_struct.pack(data_length, data)
            self.transport.sendall(data)


    def on_connection_closed(self):
        """called when peer closed the connect"""
        raise NotImplementedError()

    def on_connection_lost(self):
        """called when lost peer"""
        raise NotImplementedError()

    def on_data(self, data):
        """called when data received. (stripped the 4 bytes header)"""
        raise NotImplementedError()


    def terminate(self):
        gevent.killall(self.jobs)
        self.transport.close()
        self.kill()

    def _run(self):
        job_recv = gevent.spawn(self.recv_data)
        job_send = gevent.spawn(self.send_data)

        def _exit(glet):
            job_recv.unlink(_exit)
            job_send.unlink(_exit)
            self.terminate()

        job_recv.link(_exit)
        job_send.link(_exit)

        self.jobs.append(job_recv)
        self.jobs.append(job_send)

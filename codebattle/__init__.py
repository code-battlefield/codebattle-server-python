# -*- coding: utf-8 -*-

__author__ = 'Wang Chao'
__date__ = '14-6-22'

import gevent
import logging

from codebattle.observer import ObserverManager
from codebattle.player import PlayerManager

LOG_LEVEL_TABLE = {
    'NOTSET': logging.NOTSET,
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}


class CodeBattle(object):
    def __init__(self, log_level='DEBUG'):
        self.build_logger(log_level)

    def run(self):
        ob = ObserverManager(11011)
        ob.start()

        p = PlayerManager(11012)
        p.start()
        gevent.wait()


    def build_logger(self, log_level):
        level = LOG_LEVEL_TABLE[log_level]

        logger = logging.getLogger('codebattle')
        logger.setLevel(level)

        fmt = logging.Formatter('%(asctime)s %(levelname)s %(name)s:  %(message)s')
        stream_handle = logging.StreamHandler()
        stream_handle.setLevel(level)
        stream_handle.setFormatter(fmt)

        logger.addHandler(stream_handle)

        logger.info("CodeBattle Start")

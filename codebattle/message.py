# -*- coding: utf-8 -*-

__author__ = 'Wang Chao'
__date__ = '14-6-22'


from protomsg import observer_pb2, api_pb2, marine_pb2


OBSERVER_CREATE_ROOM = observer_pb2.createroom
OBSERVER_JOIN_ROOM = observer_pb2.joinroom
OBSERVER_MARINE_REPORT = observer_pb2.marinereport

PLAYER_JOIN_ROOM = api_pb2.joinroom
PLAYER_CREATE_MARINE = api_pb2.createmarine
PLAYER_OPERATE_MARINE = api_pb2.marineoperate


def marine_obj_to_protobuf(marine, own=True):
    """

    :param marine: codebattle.marine.Marine
    """
    msg = marine_pb2.Marine()
    msg.id = marine.id
    msg.hp = marine.hp
    msg.position.x, msg.position.z = marine.position
    msg.status = marine.status

    if own:
        msg.targetPosition.x, msg.targetPosition.z = marine.target_position
        msg.flaresAmount = marine.flares_amount

    msg.role = marine.role

    return msg


class ObserverMessage(object):
    def unpack(self, data):
        msg = observer_pb2.Cmd()
        msg.ParseFromString(data)

        if msg.cmd == OBSERVER_CREATE_ROOM:
            return OBSERVER_CREATE_ROOM, msg.crm

        if msg.cmd == OBSERVER_JOIN_ROOM:
            return OBSERVER_JOIN_ROOM, msg.jrm

        return OBSERVER_MARINE_REPORT, msg.mrt


    def pack_create_room_message(self, ret=0, room_id=None, size=None):
        response = observer_pb2.Message()
        response.msg = observer_pb2.cmdresponse
        response.response.ret = 0
        response.response.cmd = OBSERVER_CREATE_ROOM
        response.response.crmResponse.id = room_id
        response.response.crmResponse.size.x = size[0]
        response.response.crmResponse.size.z = size[1]
        return response.SerializeToString()


    def pack_create_marine_message(self, marines, color):
        msg = observer_pb2.Message()
        msg.msg = observer_pb2.createmarine
        msg.marines.color = color
        for m in marines:
            msg_m = msg.marines.marine.add()
            msg_m.MergeFrom(marine_obj_to_protobuf(m))

        return msg.SerializeToString()

    def pack_sence_update_message(self, marine):
        msg = observer_pb2.Message()
        msg.msg = observer_pb2.senceupdate
        msg_m = msg.update.marine.add()
        msg_m.MergeFrom(marine_obj_to_protobuf(marine))
        return msg.SerializeToString()



observer = ObserverMessage()


class PlayerMessage(object):
    def unpack(self, data):
        msg = api_pb2.Cmd()
        msg.ParseFromString(data)

        if msg.cmd == PLAYER_JOIN_ROOM:
            return PLAYER_JOIN_ROOM, msg.jrm

        if msg.cmd == PLAYER_CREATE_MARINE:
            return PLAYER_OPERATE_MARINE, msg.cme

        return PLAYER_OPERATE_MARINE, msg.opt


    def pack_join_room_error_response(self, error_code):
        msg = api_pb2.Message()
        msg.msg = api_pb2.joinroom
        msg.response.ret = error_code
        return msg.SerializeToString()


    def pack_join_room_response(self, room_id, map_size, marines):
        msg = api_pb2.Message()
        msg.msg = api_pb2.cmdresponse

        msg.response.ret = 0
        msg.response.cmd = api_pb2.joinroom

        jrm = msg.response.jrmResponse
        jrm.id = room_id
        jrm.size.x, jrm.size.z = map_size
        for m in marines:
            msg_s = jrm.marines.add()
            msg_s.MergeFrom(marine_obj_to_protobuf(m))
        return msg.SerializeToString()



    def pack_operate_marine_response(self, error_code):
        msg = api_pb2.Message()
        msg.msg = api_pb2.cmdresponse
        msg.response.ret = error_code
        msg.response.cmd = api_pb2.marineoperate
        return msg.SerializeToString()


    def pack_start_battle_message(self):
        msg = api_pb2.Message()
        msg.msg = api_pb2.startbattle
        return msg.SerializeToString()


    def pack_sence_update_message(self, my_marines, other_marines):
        msg = api_pb2.Message()
        msg.msg = api_pb2.senceupdate
        for m in my_marines:
            msg_own = msg.update.own.add()
            msg_own.MergeFrom(marine_obj_to_protobuf(m))
        for m in other_marines:
            msg_oth = msg.update.others.add()
            msg_oth.MergeFrom(marine_obj_to_protobuf(m, own=False))

        return msg.SerializeToString()


    def pack_end_battle_message(self, reason, win):
        msg = api_pb2.Message()
        msg.msg = api_pb2.endbattle
        msg.endbattle.reason = reason
        msg.endbattle.win = win
        return msg.SerializeToString()


player = PlayerMessage()

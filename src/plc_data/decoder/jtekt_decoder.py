#!/usr/bin/env python3
# coding: utf-8
# Copyright (c) 2019-2020 Latona. All rights reserved.

from ..tcp_packet import SendPacket, RcvPacket
from aion.logger import lprint

class JtektPlcData:
    byte_order = 'little'
    encode = "shift_jis"
    data_size = 0  # ファイル上の1データのサイズ
    status = {}
    command = ""

    def __init__(self, req, res):
        if res:
            self.status = res.get_status()
            self._set_binary(res.get_data())
        else:
            self._set_binary(bytes(self.data_size))
        if req:
            self.array_no = int.from_bytes(req.array_no, byteorder="big")
            self.command = req.command.hex()

    def _set_binary(self, binary):
        self.binary = binary

    def _set_bytes(self, pos, value):
        data = bytearray(self.binary)
        data[pos:pos + len(value)] = value
        self.binary = bytes(data)

    def is_success(self):
        return True if self.status and self.status.get("ResponseStatus") == "00" else False

    def to_array(self):
        return {}

    def get_status(self):
        return {"ArrayNo": self.array_no, **self.status}

    def _string_decoder(self, byte):
        return byte.decode(self.encode).replace("\x00", "")

    @staticmethod
    def create_request(data):
        header_list = {}
        try:
            for array in data.get("arrayNo"):
                header = SendPacket()
                header.set_body(bytearray(2))
                header.command = bytes.fromhex(data.get("command"))
                header.define_property("array_no", 5, 2, int(array,16))
                header.block_num = 3
                header_list[array] = header
        except Exception as e:
            lprint("cant convert to hex: " + str(e))
            lprint(traceback.format_exc())
            return []
        return header_list

    @staticmethod
    def create_datalist(resp_list, decoder_class):
        robot_data_list = []
        for req, res_raw in resp_list:
            res = RcvPacket()
            res.set_binary(res_raw)
            robot_data_list.append(decoder_class(req, res))
        return robot_data_list


class JtektPlcDataMulti:
    byte_order = 'little'
    encode = "shift_jis"
    data_size = 0  # ファイル上の1データのサイズ
    status = {}
    command = ""

    def __init__(self, req, res):
        if res:
            self.status = res.get_status()
            self._set_binary(res.get_data())
        else:
            self._set_binary(bytes(self.data_size))
        if req:
            self.array_no = int.from_bytes(req.array_no, byteorder="big")
            self.head_binary = req.get_data()
            self.command = req.command.hex()

    def _set_binary(self, binary):
        self.binary = binary

    def _set_bytes(self, pos, value):
        data = bytearray(self.binary)
        data[pos:pos + len(value)] = value
        self.binary = bytes(data)

    def is_success(self):
        return True if self.status and self.status.get("ResponseStatus") == "00" else False

    def to_array(self):
        return {}

    def get_status(self):
        return {"ArrayNo": self.array_no, **self.status}

    def _string_decoder(self, byte):
        return byte.decode(self.encode).replace("\x00", "")

    @staticmethod
    def create_request(data):
        header_list = {}
        try:
            array_list = data.get("arrayNo")
            array_bytes = b''
            for array in array_list:
                array_bytes += bytes.fromhex(array)[::-1]
            header = SendPacket()
            header.command = bytes.fromhex(data.get("command"))
            header.block_num = len(array_bytes)+1
            header.array_no = bytes.fromhex(array_list[0])[::-1]
            header.set_body(array_bytes)
            header_list[array_list[0]] = header
        except Exception as e:
            lprint("cant convert to hex: " + str(e))
            lprint(traceback.format_exc())
            return []
        return header_list

    @staticmethod
    def create_datalist(resp_list, decoder_class):
        robot_data_list = []
        req, res_raw = resp_list[0]
        res = RcvPacket()
        res.set_binary(res_raw)
        robot_data_list = decoder_class(req, res)
        return robot_data_list


class JtektPlcDataList:
    def __init__(self, command, expire_time, robot_data_list):
        self.expire_time = expire_time
        self.data_list = robot_data_list
        if isinstance(command, bytes):
            command = command.hex()
        self.command = command
        #self.is_success = all([d.is_success() for d in self.data_list])
        self.is_success = self.data_list.is_success()

    def get_header(self):
        return {
            "Command": self.command,
            "Result": self.is_success,
            "ExpireTime": self.expire_time,
            "BaseObjectType": "",
            "ComponentType": "",
            "MotionDeviceSystemType": "",
            "MotionDeviceIdentifier": "",
            "MotionDeviceType": "",
            "ComponentName": "",
            "Manufacturer": "",
            "Model": "",
            "DataForm": "16bit_integer",
        }

    def to_json(self):
        #robot_data_list = [d.to_array() if d.is_success() else d.get_status() for d in self.data_list]
        return {**self.get_header(), **{"RobotData": self.data_list.to_array()}}


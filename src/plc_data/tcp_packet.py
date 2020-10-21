#!/usr/bin/env python3
# coding: utf-8

# Copyright (c) 2019-2020 Latona. All rights reserved.

def set_length(val, length):
    if len(val) > length:
        raise ValueError(
            "value is too large (set length: %d, real length: %d)", len(val), length)
    return val.ljust(length, b'\00')


class JtektTcpPacket:
    def __init__(self):
        self.binary = bytearray(5)
        self.header_size = 5
        self.data_size = 2

        # set main header
        index = 0
        index = self.define_property("direction", index, 1, 0)
        index = self.define_property("status", index, 1, 0)
        index = self.define_property("block_num", index, 2, 0)
        index = self.define_property("command", index, 1, 0)

    def set_binary(self, binary):
        self.binary = binary
        self.data_size = len(binary) - self.header_size
        return True

    def set_body(self, binary):
        self.binary += binary
        self.data_size = len(binary)
        return True

    def getter(self, start, length):
        end = start + length
        if len(self.binary) >= end and len(self.binary) >= start > end:
            raise IndexError("out of range")
        return bytes(self.binary[start:end])[::-1]

    def setter(self, start, length, val):
        end = start + length
        if isinstance(val, int):
            self.binary[start:end] = set_length(
                val.to_bytes(length, 'little'), length)
        elif isinstance(val, str):
            self.binary[start:end] = set_length(
                bytes.fromhex(val), length)[::-1]
        elif isinstance(val, bytes):
            self.binary[start:end] = set_length(val, length)
        else:
            raise ValueError("cant set value")

    def define_property(self, name, start, length, initial_value=None):
        end = start + length

        def getter(in_self):
            return in_self.getter(start, length)

        def setter(in_self, value):
            return in_self.setter(start, length, value)

        setattr(self.__class__, name, property(getter, setter))
        self.setter(start, length, initial_value)

        return end

    def get_packet(self):
        return bytes(self.binary)

    def get_data(self):
        if self.header_size is None or self.data_size is None:
            raise IndexError("cant get header size or data size")
        header_size = self.header_size
        data_size = self.data_size
        return self.binary[header_size:header_size + data_size]


class SendPacket(JtektTcpPacket):
    def __init__(self):
        super().__init__()


class RcvPacket(JtektTcpPacket):
    def __init__(self):
        super().__init__()

    def get_status(self):
        res = {
            "ResponseStatus": self.status.hex(),
        }
        return res

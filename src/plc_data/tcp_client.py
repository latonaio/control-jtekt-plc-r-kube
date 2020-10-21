#!/usr/bin/env python3
# coding: utf-8

# Copyright (c) 2019-2020 Latona. All rights reserved.

import asyncio
from aion.logger import lprint

class TCPClient(asyncio.Protocol):
    def __init__(self, send, on_response):
        self.send = send
        self.command = send.command.hex()
        self.array_no = send.array_no.hex()
        self.on_response = on_response

    def connection_made(self, transport):
        lprint("[client] create connection and send packet")
        pkt = self.send.get_packet()
        lprint(pkt.hex())
        transport.write(pkt)

    def data_received(self, data):
        lprint(data.hex())
        lprint(f"[client] get response: (command:{self.command})")
        self.on_response.set_result((self.send, data))

    def error_received(self, exc):
        lprint(f'[client] Error received ({self.command}):')

    def connection_lost(self, exc):
        lprint(f"[client] Connection closed ({self.command})")


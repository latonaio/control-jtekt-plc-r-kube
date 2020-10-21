#!/usr/bin/env python3
# coding: utf-8

# Copyright (c) 2019-2020 Latona. All rights reserved.

import asyncio
import os
from time import sleep
from aion.microservice import main_decorator, Options
from . import send_command

SERVICE_NAME = "control-jtekt-plc-r"
ADDRESS = os.environ.get("PLC_ADDRESS", "192.168.1.2")
PORT = int(os.environ.get("PLC_PORT", 1025))
AION_HOME = os.environ.get("AION_HOME", "/var/lib/aion/")
JSON_PATH = os.path.join(
    AION_HOME,
    "Data",
    SERVICE_NAME+"_1",
    "config/command_list.json")
TRIGGER_PATH = os.path.join(
    AION_HOME,
    "Data",
    SERVICE_NAME+"_1",
    "config/trigger_list.json")


@main_decorator(SERVICE_NAME)
def main(opt: Options):
    conn = opt.get_conn()
    num = opt.get_number()
    kanban = conn.set_kanban(SERVICE_NAME, num)
    loop = asyncio.get_event_loop()
    y = send_command.JtektPlcCommunicator(
        JSON_PATH, ADDRESS, PORT, loop, __file__, TRIGGER_PATH
    )
    y.start_to_send(conn)

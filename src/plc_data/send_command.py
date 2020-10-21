#!/usr/bin/env python3
# coding: utf-8

# Copyright (c) 2019-2020 Latona. All rights reserved.

import asyncio
import json
import os
import traceback
from datetime import datetime
from importlib import import_module
from aion.kanban import kanban
from aion.logger import lprint
from .tcp_packet import SendPacket, RcvPacket
from .tcp_client import TCPClient
from .decoder import JtektPlcDataList


BUF_SIZE = 4096
DEFAULT_TIMEOUT = 1


def read_config_json(json_path):
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError as e:
        lprint(str(e))
        return None
    except json.JSONDecodeError as e:
        lprint(str(e))
        return None

    command = data.get("command")
    if command is None:
        lprint(f"there is no command data: {json_path}")
        return None

    return command


def create_header(data):
    header_list = {}
    try:
        for array in data.get("arrayNo"):
            header = SendPacket()
            header.command = bytes.fromhex(data.get("command"))
            header.define_property("array_no", 5, 2, int(array,16))
            header.block_num = 3
            header_list[array] = header
    except Exception as e:
        lprint("cant convert to hex: " + str(e))
        lprint(traceback.format_exc())
        return []
    return header_list


def get_all_header_list_by_json(json_path):
    header_list = {}
    conf = read_config_json(json_path)
    if conf is None:
        return {}
    for data in conf:
        command = data.get("command")
        dec_data_library = import_module(
            "src.plc_data.decoder.jtekt_decoder_0x" + command)
        decoder_class = dec_data_library.PlcData
        if data.get("expire_time") is None or data.get("interval") is None:
            lprint(
                f"there is no expire_time or interval (command:{command})")
            continue
        headers = decoder_class.create_request(data)
        if headers is None:
            lprint(f"cant get header data (command:{command})")
            continue
        header_list[command] = {
            "headers": headers,
            "interval": data.get("interval"),
            "expire_time": data.get("expire_time"),
            "decoder": decoder_class,
        }
    return header_list


class JtektPlcCommunicator:
    def __init__(self, json_path, address, port, loop, main_path, trigger_path):
        self.header_list = get_all_header_list_by_json(json_path)
        self.send_queue = asyncio.Queue()
        self.rcv_queue = asyncio.Queue()
        self.address = address
        self.port = port
        self.loop = loop
        self.main_path = main_path
        self.trigger_path = trigger_path

        self.json_path = json_path
        self.task_list = {}
        self.last_file_updated = os.path.getmtime(json_path)
        self.data_list = []
        self.timestamp = None

    def start_to_send(self, conn):
        if self.header_list is None:
            return False
        for command, header_data in self.header_list.items():
            self.task_list[command] = asyncio.ensure_future(
                self.set_queue_by_interval(command, header_data))
        #asyncio.ensure_future(self.reload_command_list())
        asyncio.ensure_future(self.send_request())
        self.loop.run_until_complete(self.output_status_json(conn))

    async def reload_command_list(self):
        while True:
            # wait
            lprint("check command list file reload><><>")
            await asyncio.sleep(1)
            # check file update
            tmp = os.path.getmtime(self.json_path)
            if self.last_file_updated != tmp:
                lprint("command list file reload><><>")
                self.last_file_updated = tmp
                # stop old task
                for command, header_data in self.header_list.items():
                    self.task_list[command].cancel()
                # update header list
                self.header_list = get_all_header_list_by_json(self.json_path)
                # start new task
                for command, header_data in self.header_list.items():
                    self.task_list[command] = asyncio.ensure_future(
                        self.set_queue_by_interval(command, header_data))

    async def set_queue_by_interval(self, command, header_data):
        interval = header_data.get("interval")
        expire_time = header_data.get("expire_time")
        header_list = header_data.get("headers")
        decoder_class = header_data.get("decoder")
        if interval is None or not header_list:
            lprint("invalid input in set_queue_by_interval")
            return False

        while True:
            await self.send_queue.put((command, header_list, decoder_class, expire_time))
            if interval == 0:
                break
            await asyncio.sleep(interval / 1000)

    async def send_request(self):
        while True:
            command, header_list, decoder_class, expire_time = await self.send_queue.get()
            if not isinstance(header_list, dict):
                raise TypeError("header to list")
            lprint(f"[client] send to robot: {command}")

            resp_list = []

            async def get_response(wait_func):
                # return : request packet (SendPacket) , response packet (bytes)
                resp_list.append(await wait_func)

            # send all array no
            for array_no, header in header_list.items():
                on_response = self.loop.create_future()
                try:
                    transport, protocol = await self.loop.create_connection(
                        lambda: TCPClient(header, on_response), self.address, self.port)
                except OSError as e:
                    lprint(str(e))
                    continue
                try:
                    await asyncio.wait_for(get_response(on_response), DEFAULT_TIMEOUT)
                except asyncio.TimeoutError:
                    lprint(f"timeout to receive: {header.command.hex()}")
                    pass
                finally:
                    transport.close()
                # safety interval
                await asyncio.sleep(0.1)

            # set to data decoder class
            robot_data_list = decoder_class.create_datalist(resp_list, decoder_class)

            data_list = JtektPlcDataList(
                command, expire_time, robot_data_list)

            await self.rcv_queue.put((data_list, datetime.now().isoformat()))

    async def output_status_json(self, conn):
        #trigger_list = read_config_json(
        #    self.trigger_path) if self.trigger_path else []
        previous_executed = {}

        while True:
            data_list, timestamp = await self.rcv_queue.get()
            robot_data = data_list.to_json()

            metadata_sets = {}
            metadata_sets["RobotData"] = robot_data
            metadata_sets["timestamp"] = timestamp
            conn.output_kanban(
                result=True,
                metadata=metadata_sets
            )

"""
            # start check trigger
            for row in trigger_list:
                trigger = row.get('trigger')
                connection_key = row.get('connectionKey')
                metadata = row.get('metadata', {})

                # check commnad no
                if robot_data.get('Command') and \
                        robot_data.get('Command') == trigger.get('command'):
                    for command in robot_data.get('RobotData') \
                            if robot_data.get('RobotData') else []:
                        # check array no
                        if command.get('ArrayNo') is not None and \
                                command.get('ArrayNo') == int(trigger.get('arrayNo'),16):
                            element_name = trigger.get("elementName")
                            element_value = command.get(element_name)
                            state_tag = "%s:%s:%s:%s" % (trigger.get('command'),
                                                         trigger.get(
                                                             'arrayNo'), element_name,
                                                         trigger.get("conditions"))
                            # check conditions
                            if str(element_value).isdecimal():
                                is_condition = eval(str(element_value) + trigger.get("conditions"))
                            else:
                                lprint("element value is not number!")
                                is_condition = eval(str(f"'{element_value}'") + trigger.get("conditions"))

                            lprint(f"[condition] is {str(is_condition)}")
                            if is_condition:
                                # check previous state
                                if trigger.get("always", 0) != 1:  # 1:always,0:on_change
                                    if previous_executed.get(state_tag):
                                        continue
                                previous_executed[state_tag] = True

                                metadata_sets = metadata
                                metadata_sets["RobotData"] = robot_data
                                metadata_sets["timestamp"] = timestamp

                                lprint("[RobotData]", metadata_sets.get("RobotData"))
                                # call next service
                                if connection_key:
                                    conn.output_kanban(
                                        result=True,
                                        connection_key=connection_key,
                                        metadata=metadata_sets
                                    )
                                else:
                                    conn.output_kanban(
                                        result=True,
                                        metadata=metadata_sets
                                    )
                                lprint(f'[client] output kanban')
                            else:
                                lprint("[client ]condition is not true")
                                previous_executed[state_tag] = False
"""


#!/usr/bin/env python
'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

from infrasim.ipmicons import sdr
from infrasim.ipmicons.command import Command_Handler
from infrasim.ipmicons.common import msg_queue
import unittest

ch = Command_Handler()


class test_ipmi_console(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def test_sensor_value_get_discrete(self):
        sensor_d = sdr.build_sensors(name="discrete_sample",
                                     ID=0x10,
                                     mc=32,
                                     value="0xca10",
                                     tp=0x00)
        sensor_d.set_event_type(0x6f)

        ch.get_sensor_value(["0x10"])
        assert "0xca10" in msg_queue.get()

    def test_sensor_value_get_analog(self):
        sensor_a = sdr.build_sensors(name="analog_sample",
                                     ID=0x11,
                                     mc=32,
                                     value=0x63,
                                     tp=0x00)
        sensor_a.set_event_type(0x01)
        sensor_a.set_m_lb(0x58)
        sensor_a.set_m_ub(0x00)
        sensor_a.set_b_lb(0x00)
        sensor_a.set_b_ub(0x00)
        sensor_a.set_exp(0x00)
        sensor_a.set_su2(18)

        ch.get_sensor_value(["0x11"])
        assert "analog_sample : 8712.000 RPM" in msg_queue.get()

#!/usr/bin/python
'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''

from .common import msg_queue, send_ipmi_sim_command
import random
import threading
from .sel import SEL
from functools import wraps

sensor_unit = {
    0:  'percent',    34: 'm',                  68: 'megabit',
    1:  'degrees C',  35: 'cu cm',              69: 'gigabit',
    2:  'degrees F',  36: 'cu m',               70: 'byte',
    3:  'degrees K',  37: 'liters',             71: 'kilobyte',
    4:  'Volts',      38: 'fluid ounce',        72: 'megabyte',
    5:  'Amps',       39: 'radians',            73: 'gigabyte',
    6:  'Watts',      40: 'steradians',         74: 'word (data)',
    7:  'Joules',      41: 'revolutions',        75: 'dword',
    8:  'Coulombs',    42: 'cycles',             76: 'qword',
    9:  'VA',          43: 'gravities',          77: 'line (re. mem.  line)',
    10: 'Nits',        44: 'ounce',              78: 'hit',
    11: 'lumen',       45: 'pound',              79: 'miss',
    12: 'lux',         46: 'ft-lb',              80: 'retry',
    13: 'Candela',     47: 'oz-in',              81: 'reset',
    14: 'kPa',         48: 'gauss',              82: 'overrun / overflow',
    15: 'PSI',         49: 'gilberts',           83: 'underrun',
    16: 'Newton',      50: 'henry',              84: 'collision',
    17: 'CFM',         51: 'millihenry',         85: 'packets',
    18: 'RPM',         52: 'farad',              86: 'messages',
    19: 'Hz',          53: 'microfarad',         87: 'characters',
    20: 'microsecond', 54: 'ohms',               88: 'error',
    21: 'millisecond', 55: 'siemens',            89: 'correctable error',
    22: 'second',      56: 'mole',               90: 'uncorrectable error',
    23: 'minute',      57: 'becquerel',          91: 'fatal error',
    24: 'hour',        58: 'PPM (parts/million)',  92: 'grams',
    25: 'day',         59: 'reserved',
    26: 'week',        60: 'Decibels',
    27: 'mil',         61: 'DbA',
    28: 'inches',      62: 'DbC',
    29: 'feet',        63: 'gray',
    30: 'cu in',      64: 'sievert',
    31: 'cu feet',    65: 'color temp deg K',
    32: 'mm',        66: 'bit',
    33: 'cm',        67: 'kilobit',
}


class with_type(object):
    """
    This is a decorator for class Sensor function's constraints.
    Only with certain types, the funtions run, or TypeError shall
    be raised.
    """

    def __init__(self, *type):
        self.expect_type_list = type

    def __call__(self, fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            obj_self = args[0]
            if obj_self.get_event_type() in self.expect_type_list:
                return fn(*args, **kwargs)
            else:
                raise TypeError('Sensor is "{}", while function "{}" '
                                'requires "{}"'.
                                format(obj_self.get_event_type(),
                                       fn.__name__,
                                       self.expect_type))
        return wrapper


class Sensor:
    def __init__(self, name, ID, value, tp):
        self.name = name
        self.ID = ID
        self.tp = tp
        self.lock = threading.Lock()
        self.lock_sensor_write = threading.Lock()
        self.condition = threading.Condition()
        self.time_cond = threading.Condition()
        self.mode = "user"
        self.value = value
        self.quit = False
        self.lnr = 0
        self.lnc = 0
        self.lc = 0
        self.unc = 0
        self.uc = 0
        self.unr = 0
        self.sel = SEL()

    def set_quit(self, flag):
        self.quit = flag

    def set_fault_level(self, fl):
        self.fault_level = fl

    def get_mc(self):
        return self.mc

    def set_mc(self, mc):
        self.mc = mc

    def get_lun(self):
        return self.lun

    def set_lun(self, lun):
        self.lun = lun

    def get_mode(self):
        return self.mode

    def set_mode(self, mode):
        self.mode = mode

    def get_name(self):
        return self.name

    def get_num(self):
        return self.ID

    def get_type(self):
        return self.tp

    def set_type(self, tp):
        self.tp = tp

    def set_event_type(self, event):
        self.event_type = event

    def get_event_type(self):
        if self.event_type == 0x0:
            return "NA"
        elif self.event_type == 0x1:
            return "threshold"
        else:
            return "discrete"

    def initialize_sel(self):
        self.sel.set_mc(self.mc)
        self.sel.set_gid_1(self.mc)
        self.sel.set_gid_2(self.lun)
        self.sel.set_sensor_type(self.tp)
        self.sel.set_sensor_num(self.ID)
        self.sel.set_event_type(self.event_type)

    def get_sel(self):
        if self.sel.check_event_type() is False:
            return False

        if self.sel.check_sensor_type() is False:
            return False

        self.sel.get_event()

    def set_sel(self, event_id, event_dir):
        if self.sel.check_event_type() is False:
            return False

        if self.sel.check_sensor_type() is False:
            return False

        if self.sel.set_event_data(event_id) is False:
            return False

        self.sel.set_event_dir(event_dir)
        self.sel.send_event()

    @with_type('threshold')
    def set_threshold_value(self, value):
        self.value = value
        command = "sensor_set_value " + hex(self.mc) + " " \
              + hex(self.lun) + " " + hex(self.ID) + " " + hex(value) + " 0x01\n"
        send_ipmi_sim_command(command)

    @with_type('discrete')
    def set_discrete_value(self, value):
        """
        Set discrete sensor value
        :param value: in format of 2 byte little endian, e.g. 0xca10
        """
        if len(value) != 6 or not value.startswith('0x'):
            raise ValueError('Discrete sensor value should be in format '
                             'of 2 bytes in little endian, e.g. 0x1ac0')

        # Sensor reading in big endian binary
        # e.g.
        # Original reading is 0xca10 in little endian
        # This value in bin is
        # 0001 0000 1100 1010
        #  1    0    c    a
        # bit 0 > 15
        # bit 0 is reserved, bit 1 is state 14 ... bit 15 is state 0
        value_in_bin = "{0:b}".format(int(self.value[4:6]+self.value[2:4], 16)).zfill(16)
        value_to_set = "{0:b}".format(int(value[4:6]+value[2:4], 16)).zfill(16)
        list_diff = []

        for i in range(0, 15):
            state_id = i
            bit_orig = value_in_bin[15-state_id]
            bit_targ = value_to_set[15-state_id]
            if bit_orig != bit_targ:
                list_diff.append((state_id, int(bit_targ)))

        self.lock_sensor_write.acquire()
        self.value = value
        for diff in list_diff:
            command = "sensor_set_bit " + hex(self.mc) + " " + hex(self.lun) \
                      + " " + hex(self.ID) + " " + str(diff[0]) + " " \
                      + str(diff[1]) + " 0x01\n"
            send_ipmi_sim_command(command)
        self.lock_sensor_write.release()

    @with_type('discrete')
    def set_state(self, state_id, state_bit):
        """
        Set disrete sensor's state in id to a certain bit
        :param state_id: 0-14, according to IPMI spec 2.0
        :param state_bit: 1 or 0
        """
        if state_id not in range(0, 15):
            raise ValueError('State id must be in 0-14 according to '
                             'IPMI 2.0 specification')
        if state_bit not in range(0, 2):
            raise ValueError('Bit to set must be 0 or 1')

        value_in_int = int(self.value[4:6]+self.value[2:4], 16)

        if state_bit:
            mask = 1 << state_id
            value_in_int = value_in_int | mask
        else:
            mask = ~(1 << state_id)
            value_in_int = value_in_int & mask

        value_in_hex = hex(value_in_int)[2:].zfill(4)

        self.lock_sensor_write.acquire()
        self.value = "0x"+value_in_hex[2:4]+value_in_hex[0:2]
        command = "sensor_set_bit " + hex(self.mc) + " " + hex(self.lun) \
                  + " " + hex(self.ID) + " " + str(state_id) + " " \
                  + str(state_bit) + " 0x01\n"
        send_ipmi_sim_command(command)
        self.lock_sensor_write.release()

    def set_raw_value(self, raw_value):
        self.value = raw_value

    def get_value(self):
        return self.value

    def set_cap(self, cap):
        self.cap = cap

    def get_cap(self):
        return self.cap

    def set_ltm_lb(self, ltm_lb):
        self.ltm_lb = ltm_lb

    def get_ltm_lb(self):
        return self.ltm_lb

    def set_ltm_ub(self, ltm_ub):
        self.ltm_ub = ltm_ub

    def get_ltm_ub(self):
        return self.ltm_ub

    def set_utm_lb(self, utm_lb):
        self.utm_lb = utm_lb

    def get_utm_lb(self):
        return self.utm_lb

    def set_utm_ub(self, utm_ub):
        self.utm_ub = utm_ub

    def get_utm_ub(self):
        return self.utm_ub

    # set sensor unit 1
    # bit 6 and bit 7 - Analog (numeric) Data Format
    # 00b = unsigned
    # 01b = 1's complement (signed) (-127 - +127)
    # 10b = 2's complement (signed) (-128 - +127)
    # 11b = Does not return analog (numeric) reading
    def set_su1(self, su1):
        self.su1 = su1

    # set sensor unit 2
    def set_su2(self, su2):
        self.su2 = su2

    # set M low 8 bits
    def set_m_lb(self, m_lb):
        self.m_lb = m_lb

    # set M high 2 bits
    def set_m_ub(self, m_ub):
        self.m_ub = m_ub

    # set B low 8 bits
    def set_b_lb(self, b_lb):
        self.b_lb = b_lb

    # set B high 2 bits
    def set_b_ub(self, b_ub):
        self.b_ub = b_ub

    def set_accuracy(self, accuracy):
        self.accuracy = accuracy

    def set_exp(self, exp):
        self.exp = exp

    # the function will return the lambda of the linearization
    def get_reading_factor(self):
        M = ((self.m_ub & 0xc0) << 2) + self.m_lb
        b_sig = (self.b_ub >> 7) & 0x1
        if b_sig == 1:
            B = ~((((self.b_ub & 0x40) << 2) + self.b_lb) ^ 0x1ff)
        else:
            B = ((self.b_ub & 0xc0) << 2) + self.b_lb

        Rex_sig = (self.exp >> 7) & 0x1
        if Rex_sig == 1:
            Rexpo = ~(((self.exp & 0x70) >> 4) ^ 0x07)
        else:
            Rexpo = (self.exp & 0xf0) >> 4

        Bexpo = self.exp & 0x0f

        # formula: convert RAW value to human readable value
        formula_1 = lambda x: (M*x+B*10**Bexpo)*10**Rexpo
        # formula: convert human readable value to RAW value
        formula_2 = lambda x: (x / (10**Rexpo) - B*10**Bexpo) / M
        return (formula_1, formula_2)

    #settable threshold mask
    def set_stm(self, stm):
        self.stm = stm

    def get_stm(self):
        return self.stm

    #readable threshold mask
    def set_rtm(self, rtm):
        self.rtm = rtm

    def get_rtm(self):
        return self.rtm

    def get_thres_ac_supp(self):
        value = (self.cap >> 2) & 0x3
        if value == 0x0:
            return "none"
        elif value == 0x1:
            return "readable"
        elif value == 0x2:
            return "settable"
        elif value == 0x3:
            return "fixed"

    # set lower non cirtical threshold
    def set_lnc(self, lnc):
        self.lnc = lnc

    def get_lnc(self):
        return self.lnc

    # set lower cirtical threshold
    def set_lc(self, lc):
        self.lc = lc

    def get_lc(self):
        return self.lc

    # set lower non-recoverable threshold
    def set_lnr(self, lnr):
        self.lnr = lnr

    def get_lnr(self):
        return self.lnr

    #set upper non-critical threshold
    def set_unc(self,unc):
        self.unc = unc

    def get_unc(self):
        return self.unc

    #set upper cirtical threshold
    def set_uc(self,uc):
        self.uc = uc

    def get_uc(self):
        return self.uc

    #set upper non-recoverable threshold
    def set_unr(self,unr):
        self.unr = unr

    def get_unr(self):
        return self.unr

    def get_unit(self):
        # Sensor Unit
        if self.get_event_type() == 'threshold':
            try:
                return sensor_unit[self.su2]
            except KeyError:
                return 'unknown'
        else:
            return 'discrete'

    def output_info(self):
        # Sensor Name
        info = "{0:<20}".format(self.name)
        # Sensor ID
        info += "| {0:<10}".format(hex(self.ID))
        # sensor value
        if self.get_event_type() == 'threshold':
            value = "%.3f" % self.get_reading_factor()[0](self.value)
        elif self.get_event_type() == 'discrete':
            value = self.value
        info += "| {0:<10}".format(value)

        # Sensor Unit
        su = self.get_unit()
        info += "| {0:<20}".format(su)

        # lower non-recoverable
        lnr = 'NA'
        if self.get_event_type() == 'threshold' and self.rtm & 0x04 != 0:
            lnr = "%.3f" % self.get_reading_factor()[0](self.lnr)
        info += "| {0:<10}".format(lnr)

        # lowr critical
        lc = 'NA'
        if self.get_event_type() == 'threshold' and self.rtm & 0x02 != 0:
            lc = "%.3f" % self.get_reading_factor()[0](self.lc)
        info += "| {0:<10}".format(lc)

        # lower non-critical
        lnc = 'NA'
        if self.get_event_type() == 'threshold' and self.rtm & 0x01 != 0:
            lnc = "%.3f" % self.get_reading_factor()[0](self.lnc)
        info += "| {0:<10}".format(lnc)

        # upper non-critical
        unc = 'NA'
        if self.get_event_type() == 'threshold' and self.rtm & 0x08 != 0:
            unc = "%.3f" % self.get_reading_factor()[0](self.unc)
        info += "| {0:<10}".format(unc)

        # upper critical
        uc = 'NA'
        if self.get_event_type() == 'threshold' and self.rtm & 0x10 != 0:
            uc = "%.3f" % self.get_reading_factor()[0](self.uc)
        info += "| {0:<10}".format(uc)

        # upper non-recoverable
        unr = 'NA'
        if self.get_event_type() == 'threshold' and self.rtm & 0x20 != 0:
            unr = "%.3f" % self.get_reading_factor()[0](self.unr)
        info += "| {0}".format(unr)

        return info

    def get_random_value(self):
        s_lnr_mask = self.rtm & 0x04
        s_lcr_mask = self.rtm & 0x02
        s_lnc_mask = self.rtm & 0x01
        s_unc_mask = self.rtm & 0x08
        s_ucr_mask = self.rtm & 0x10
        s_unr_mask = self.rtm & 0x20

        # set low value
        if s_lnc_mask != 0:
            low_value = self.lnc + 1
        elif s_lcr_mask != 0:
            low_value = self.lc + 1
        elif s_lnr_mask != 0:
            low_value = self.lnr + 1
        elif (self.su1 >> 6) == 1 or (self.su1 >> 6) == 2:
            low_value = -127
        else:
            low_value = 0

        # set high value
        if s_unc_mask != 0:
            high_value = self.unc - 1
        elif s_ucr_mask != 0:
            high_value = self.uc - 1
        elif s_unr_mask != 0:
            high_value = self.unr - 1
        elif (self.su1 >> 6) == 1 or (self.su1 >> 6) == 2:
            high_value = 127
        else:
            high_value = 255

        return random.randint(low_value, high_value)

    def get_fault_value(self):
        # fault mode
        s_lnr_mask = self.rtm & 0x04
        s_lcr_mask = self.rtm & 0x02
        s_lnc_mask = self.rtm & 0x01
        s_unc_mask = self.rtm & 0x08
        s_ucr_mask = self.rtm & 0x10
        s_unr_mask = self.rtm & 0x20

        # 1's complement (-127 - 127)
        # 2's complement (-128 - 127)
        if (self.su1 >> 6) == 1 or (self.su1 >> 6) == 2:
            MAX = 0x7F
        else:
            MAX = 0xFF

        s_value = None
        if self.fault_level == 'lnc':
            if s_lnc_mask == 0:
                info = "WARN: Sensor " + str(self.name) + " did not cross " \
                    + str(self.fault_level) + " threshold since it does not exist\n"
                msg_queue.put(info)
            else:
                # Cause lnc fault - use lc as lower limit if it exists. Otherwise use 0
                if s_lcr_mask == 0:
                    s_value = random.randint(0, self.lnc)
                else:
                    s_lc = self.lc + 1
                    s_value = random.randint(s_lc, self.lnc)
        elif self.fault_level == 'lc':
            if s_lcr_mask == 0:
                info = "WARN: Sensor " + str(self.name) + " did not cross " \
                     + str(self.fault_level) + " threshold since it does not exist\n"
                msg_queue.put(info)
            else:
                # Cause lcr fault - use lnr as lower limit if it exists. Otherwise use 0
                if s_lnr_mask == 0:
                    s_value = random.randint(0, self.lc)
                else:
                    s_lnr = self.lnr + 1
                    s_value = random.randint(s_lnr, self.lc)
        elif self.fault_level == 'lnr':
            if s_lnr_mask == 0:
                info = "WARN: Sensor " + str(self.name) + " did not cross " \
                    + str(self.fault_level) + " threshold since it does not exist\n"
                msg_queue.put(info)
            else:
                # Cause lnr fault - use 0 as lower limit
                s_value = random.randint(0, self.lnr)
        elif self.fault_level == 'unc':
            if s_unc_mask == 0:
                info = "WARN: Sensor " + str(self.name) + " did not cross " \
                    + str(self.fault_level) + " threshold since it does not exist\n"
                msg_queue.put(info)
            else:
                # Cause unc fault - use ucr as upper limit if it exists. Otherwise use 255
                if s_ucr_mask == 0:
                    s_value = random.randint(self.unc, MAX)
                else:
                    s_uc = self.uc - 1
                    s_value = random.randint(self.unc, s_uc)
        elif self.fault_level == 'uc':
            if s_ucr_mask == 0:
                info = "WARN: Sensor " + str(self.name) + " did not cross " \
                     + str(self.fault_level) + " threshold since it does not exist\n"
                msg_queue.put(info)
            else:
                # Cause ucr fault - user unr as upper limit if it exists. Otherwise use 255
                if s_unr_mask == 0:
                    s_value = random.randint(self.uc, MAX)
                else:
                    s_unr = self.unr - 1
                    s_value = random.randint(self.uc, s_unr)
        else:
            if s_unr_mask == 0:
                info = "WARN: Sensor " + str(self.name) + " did not cross " \
                        + str(self.fault_level) + " threshold since it does not exist\n"
                msg_queue.put(info)
            else:
                # Cause unr fault - use 255 as upper limit
                s_value = random.randint(self.unr, MAX)
        return s_value

    def execute(self):
        while not self.quit:
            self.condition.acquire()
            try:
                if self.mode == "user": # user mode
                    self.condition.wait()
                    if self.quit == True:
                        return
                else:
                    #(lnc, unc) = self.get_lnc_unc()
                    if self.mode == "auto": # auto mode
                        s_value = self.get_random_value()
                    else: # fault mode
                        s_value = self.get_fault_value()
                        self.mode = "user"

                    if s_value == None:
                        continue

                    self.value = s_value

                    command = "sensor_set_value " + hex(self.mc) + " " \
                        + hex(self.lun) + " " + hex(self.ID) + " " + hex(s_value) + " 0x01\n"
                    send_ipmi_sim_command(command)

                    if self.mode == "auto": # auto mode
                        self.condition.wait(5)
                        if self.quit == True:
                            return
            # we release the lock so that master thread could join us
            # and release the thread resource
            finally:
                self.condition.release()

'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from .common import logger, msg_queue
from .sdr import sensor_id_map
from .sel import SEL

import common
import sel
import re


# can be achievable by multiprocessing.managers


class Command_Handler:
    def __init__(self):
        self.command_history = []

    def add_msg(self, msg):
        logger.info(msg)

    def get_sensor_instance(self, str_num, mc=int("0x20", 16)):
        """
        return sensor instance if the sensor exist
        otherwise return None
        """
        try:
            sensor_id = int(str_num, 16)
        except ValueError:
            logger.error('illegal sensor id %s' % str_num)
            return None

        if (sensor_id, mc) not in sensor_id_map:
            error_info = "sensor: {0} not exist\n".format(str_num)
            msg_queue.put(error_info)
            return None

        return sensor_id_map[(sensor_id, mc)]

    # args contain the sensor id list
    def output_sensors(self, args):
        for str_num in args:
            sensor_obj = self.get_sensor_instance(str_num)
            if sensor_obj is None:
                return
            info = sensor_obj.output_info()
            info += '\n'
            msg_queue.put(info)

    def dump_all_sensor_info(self):
        """
        dump all sensor info
        """
        for ID, sensor_obj in sensor_id_map.items():
            info = sensor_obj.output_info()
            info += '\n'
            msg_queue.put(info)

    def dump_sensor_info(self, args):
        if len(args) == 0:
            self.dump_all_sensor_info()
        self.output_sensors(args)

    def set_sensor_mode(self, args):
        if len(args) < 2:
            msg_queue.put(self.handle_sensor_mode.__doc__+'\n')
            return

        sensor_obj = self.get_sensor_instance(args[0])
        if sensor_obj is None:
            return

        # sensor mode check
        mode = args[1]
        if mode not in ['user', 'auto', 'fault']:
            msg_queue.put(self.handle_sensor_mode.__doc__+'\n')
            return

        # if mode is fault, we also need specify the fault level
        if mode == 'fault':
            if len(args) < 3:
                msg_queue.put(self.handle_sensor_mode.__doc__+'\n')
                return

            fault_level = args[2]
            if fault_level not in ['lnr', 'lc', 'lnc', 'unc', 'uc', 'unr']:
                msg_queue.put(self.handle_sensor_mode.__doc__+'\n')
                return

            sensor_obj.set_fault_level(fault_level)

        pre_mode = sensor_obj.get_mode()
        sensor_obj.set_mode(mode)
        if (mode == "auto" or mode == 'fault') and pre_mode == "user":
            logger.info('set to auto mode and wakeup sensor thread')
            # notify the sensor thread
            sensor_obj.condition.acquire()
            sensor_obj.condition.notify()
            sensor_obj.condition.release()
        sensor_name = sensor_obj.get_name()
        info = "Sensor " + str(sensor_name) + " changed to " + mode + '\n'
        msg_queue.put(info)

    def get_sensor_mode(self, args):
        if len(args) != 1:
            msg_queue.put(self.handle_sensor_mode.__doc__+'\n')
            return

        sensor_obj = self.get_sensor_instance(args[0])
        if sensor_obj is None:
            return
        sensor_mode = sensor_obj.get_mode()
        sensor_name = sensor_obj.get_name()
        info = "Sensor " + sensor_name + " mode: " + sensor_mode + '\n'
        msg_queue.put(info)
        self.add_msg(info)

    # ######### SENSOR MODE MAIN FUNCTION ##########
    def handle_sensor_mode(self, args):
        """
        Available 'sensor mode' commands:
            sensor mode set <sensorID> <user|auto|fault> <lnr | lc | lnc | unc | uc | unr>
            sensor mode get <sensorID>
        """
        if len(args) == 0:
            msg_queue.put(self.handle_sensor_mode.__doc__+'\n')
            return
        if args[0] == "set":
            self.set_sensor_mode(args[1:])
        elif args[0] == "get":
            self.get_sensor_mode(args[1:])
        else:
            return

    # ######### SET SENSOR VALUE FUNCTION ##########
    def set_sensor_value(self, args):
        """
        Set sensor value to sensor object, and then write back to
        openipmi data structure.
        :param args:
            - <sensor id>, <sensor value>: set value to the id
            - <sensor id>, state, <state id>, 1|0: set state bit to 1 or 0
        """
        sensor_obj = self.get_sensor_instance(args[0])
        if sensor_obj is None:
            return

        # switch to "user" mode if in "auto" mode
        if sensor_obj.get_mode() == "auto":
            sensor_obj.set_mode("user")
            sensor_obj.condition.acquire()
            sensor_obj.condition.notify()
            sensor_obj.condition.release()

        # <sensor id>, <sensor value>: set value to the id
        if len(args) == 2:

            if sensor_obj.get_event_type() == 'threshold':
                try:
                    analog_value = float(args[1])
                except:
                    error_info = 'illgel sensor value: {0}\n'.format(args[1])
                    msg_queue.put(error_info)
                    self.add_msg(error_info)
                    return

                formula = sensor_obj.get_reading_factor()[1]
                raw_value = int(formula(analog_value))
                info = 'sensor name: {0} formula: {1}. raw value: {2}\n'.\
                    format(sensor_obj.get_name(), formula, raw_value)
                logger.info(info)

                sensor_obj.set_threshold_value(raw_value)

            elif sensor_obj.get_event_type() == 'discrete':
                # Parameters validation
                try:
                    int(args[1], 16)
                except ValueError:
                    msg_queue.put(self.handle_sensor_value.__doc__+'\n')
                    return
                if args[1].lower().startswith("0x") and len(args[1]) == 6:
                    raw_value = args[1]
                elif not args[1].lower().startswith("0x") and len(args[1]) == 4:
                    raw_value = "0x"+args[1]
                else:
                    msg_queue.put(self.handle_sensor_value.__doc__+'\n')
                    return
                info = 'sensor name: {0} raw value: {1}\n'.\
                    format(sensor_obj.get_name(), raw_value)
                logger.info(info)

                sensor_obj.set_discrete_value(raw_value)
        # <sensor id>, state, <state id>, 1|0: set state bit to 1 or 0
        elif len(args) == 4:
            if sensor_obj.get_event_type() != 'discrete':
                info = 'Set state bit is for discrete sensor only, sensor: {} is {}'.\
                    format(args[0], sensor_obj.get_event_type())
                msg_queue.put(info)
                logger.info(info)
                return
            if args[1].lower() != 'state' \
                    or int(args[2]) not in range(0, 15) \
                    or args[3] not in ['1', '0']:
                msg_queue.put(self.handle_sensor_value.__doc__+'\n')
                return

            # Set bit for discrete sensor
            sensor_obj.set_state(int(args[2]), int(args[3]))

        else:
            msg_queue.put(self.handle_sensor_value.__doc__+'\n')
            return



    # ######### GET SENSOR VALUE FUNCTION ##########
    def get_sensor_value(self, args):
        """
        Get sensor value from sensor object, NOT from openipmi data
        structure.
        :param args: <sensor id>
        """
        if len(args) != 1:
            msg_queue.put(self.handle_sensor_value.__doc__+'\n')
            return

        sensor_obj = self.get_sensor_instance(args[0])
        if sensor_obj is None:
            return

        raw_value = sensor_obj.get_value()
        if sensor_obj.get_event_type() == 'threshold':
            formula = sensor_obj.get_reading_factor()[0]
            value = '%.3f' % formula(raw_value)
            info = "{0} : {1} {2}\n".format(sensor_obj.get_name(),
                                            value, sensor_obj.get_unit())
            self.add_msg(info)
            msg_queue.put(info)
        elif sensor_obj.get_event_type() == 'discrete':
            info = "{} : {}".format(sensor_obj.get_name(), raw_value)
            self.add_msg(info)
            msg_queue.put(info)

    # ######### SENSOR VALUE FUNCTIONS ##########
    def handle_sensor_value(self, args):
        """
        Available 'sensor value' commands:
            set: set <sensor id> <value>
                 set <sensor id> state <state id> 1|0
            get: get <sensor id>
        """
        if len(args) == 0:
            msg_queue.put(self.handle_sensor_value.__doc__+'\n')
            return
        if args[0] == "set":
            self.set_sensor_value(args[1:])
        elif args[0] == "get":
            self.get_sensor_value(args[1:])
        else:
            return

    # ######### MAIN SENSOR FUNCTIONS ##########
    def handle_sensor_command(self, args):
        """
        Available sensor commands:
            info mode value
        """
        if len(args) == 0:
            self.add_msg(self.handle_sensor_command.__doc__+'\n')
            msg_queue.put(self.handle_sensor_command.__doc__+'\n')
            return
        if args[0] == "info":
            self.dump_sensor_info(args[1:])
        elif args[0] == "mode":
            self.handle_sensor_mode(args[1:])
        elif args[0] == "value":
            self.handle_sensor_value(args[1:])
        else:
            return

    # ######### SEL FUNCTIONS ##########
    def set_oem_sel(self, args):
        try:
            record_type = int(args[0], 16)
        except ValueError:
            logger.error('record type illegal\n')
            return

        if record_type == 0x02:
            if len(args) != 9:
                msg_queue.put(self.handle_sel_command.__doc__ + '\n')
                return
            try:
                gid_1 = int(args[1], 16)
                gid_2 = int(args[2], 16)
                sensor_type = int(args[3], 16)
                sensor_num = int(args[4], 16)
                event_type = int(args[5], 16)
                event_data_1 = int(args[6], 16)
                event_data_2 = int(args[7], 16)
                event_data_3 = int(args[8], 16)
            except ValueError:
                logger.error('illegal data format\n')
                return
            sel_obj = SEL()
            sel_obj.set_sensor_type(sensor_type)
            sel_obj.set_gid_1(gid_1)
            sel_obj.set_gid_2(gid_2)
            sel_obj.set_sensor_num(sensor_num)
            sel_obj.set_event_type(event_type)
            sel_obj.set_event_data_1(event_data_1)
            sel_obj.set_event_data_2(event_data_2)
            sel_obj.set_event_data_3(event_data_3)
            sel_obj.send_event()
            return
        elif record_type >= 0xC0 and record_type <= 0xDF:
            if len(args) != 7:
                msg_queue.put(self.handle_sel_command.__doc__ + '\n')
                return
            sel_obj = sel.OEM_SEL_C0_DF()
        elif record_type >= 0xE0 and record_type <= 0xFF:
            if len(args) != 14:
                msg_queue.put(self.handle_sel_command.__doc__ + '\n')
                return
            sel_obj = sel.OEM_SEL_E0_FF()
        else:
            logger.error('unkown record type')
            return

        elements = []
        try:
            elements = [int(x, 16) for x in args[1:]]
        except ValueError:
            logger.error('illegal data format\n')
            return

        sel_obj.set_sensor_type(record_type)
        sel_obj.set_oem_defined_bytes(elements)
        sel_obj.send_event()

    def set_sel(self, args):
        """
        add SEL entry for a particular sensor or OEM sensor
        """
        if len(args) < 3:
            msg_queue.put(self.handle_sel_command.__doc__ + '\n')
            self.add_msg(self.handle_sel_command.__doc__ + '\n')
            return

        if args[0].lower() == 'oem':
            self.set_oem_sel(args[1:])
            return

        sensor_obj = self.get_sensor_instance(args[0])
        if sensor_obj is None:
            return

        try:
            event_id = int(args[1])
        except ValueError:
            logger.error('illegal event id')
            return

        # action indicate assert/deassert
        action = args[2]

        if action == 'assert':
            sensor_obj.set_sel(event_id, 0)
        elif action == 'deassert':
            sensor_obj.set_sel(event_id, 1)
        else:
            msg_queue.put(self.handle_sel_command.__doc__ + '\n')
            self.add_msg(self.handle_sel_command.__doc__ + '\n')

    def get_sel(self, args):
        if len(args) != 1:
            msg_queue.put(self.handle_sel_command.__doc__+'\n')
            return

        sensor_obj = self.get_sensor_instance(args[0])
        if sensor_obj is None:
            return

        sensor_obj.get_sel()

    def handle_sel_command(self, args):
        """
        Available 'sel' commands:
            set <sensorID> <event_id> <'assert'/'deassert'>
            get <sensorID>

            'record type 0x2'
            set oem <record_Type> <generate_id_1> <generate_id_2> <sensor_type>
                    <sensor_num> <event_type> <event_data_1> <event_data_2> <event_data_3>

            'record type 0xC0 - 0xDF'
            set oem <record_Type> <oem_byte1> <oem_byte2> <oem_byte3> <oem_byte4>
                    <oem_byte5> <oem_byte6>

            'record type 0xE0 - 0xFF'
            set oem <record_Type> <oem_byte1> <oem_byte2> <oem_byte3> <oem_byte4>
                    <oem_byte5> <oem_byte6> <oem_byte7> <oem_byte8> <oem_byte9>
                    <oem_byte10> <oem_byte11> <oem_byte12> <oem_byte13>

        """
        if len(args) == 0:
            msg_queue.put(self.handle_sel_command.__doc__ + '\n')
            self.add_msg(self.handle_sel_command.__doc__ + '\n')
            return

        if args[0] == "set":
            self.set_sel(args[1:])
        elif args[0] == "get":
            self.get_sel(args[1:])
        else:
            return

    # ######### HELP FUNCTION ##########
    def handle_help(self):
        """
        Available commands:
            sensor info
            sensor mode set <sensorID> <user>
            sensor mode set <sensorID> <auto>
            sensor mode set <sensorID> <fault> <lnr | lc | lnc | unc | uc | unr>
            sensor mode get <sensorID>
            sensor value set <sensorID> <value>
            sensor value get <sensorID>
            sel set <sensorID> <event_id> <'assert'/'deassert'>
            sel get <sensorID>
            help
            history
            quit/exit
        """
        msg_queue.put(self.handle_help.__doc__ + '\n')

    def handle_history(self):
        for i in range(0, 30):
            try:
                command = str(i) + "  " + str(self.command_history[i]) + '\n'
                msg_queue.put(command)
                self.add_msg(command)
            except IndexError:
                return

    def handle_command(self, cmd):
        cmd = cmd.strip()
        if len(cmd) == 0:
            return

        num = len(self.command_history)
        # re split
        # i.e. 'a,b;; c  d'
        args = re.split(r'[\s\,\;]+', cmd)
        if args[0] == "sensor":
            self.handle_sensor_command(args[1:])
        elif args[0] == "sel":
            self.handle_sel_command(args[1:])
        elif args[0] == "help":
            self.handle_help()
        elif args[0] == "history":
            self.handle_history()
        else:
            # TODO add more command here
            err_msg = 'illegal command\n'
            msg_queue.put(err_msg)
            self.add_msg(err_msg)
            return

        # Keep track of previous commands
        if cmd != "":
            if num >= 30:
                self.command_history.pop(0)
            else:
                num += 1

            self.command_history.append(cmd)

'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''

from .sensor import Sensor
from .common import logger, msg_queue, send_ipmitool_command
import os
import sys
import struct

sensor_list = []
sensor_name_list = []
sensor_id_list = []
sensor_name_map = {}
sensor_id_map = {}

SDR_NAME = "/tmp/sdr.bin"


def build_sensors(name, ID, mc, value, tp):
    sensor = Sensor(name, ID, value, tp)
    sensor_list.append(sensor)
    sensor_name_list.append(name)
    sensor_id_list.append(ID)
    sensor_name_map[name] = sensor
    sensor_id_map[(ID, mc)] = sensor
    return sensor


# dump sdrs into file
def dump_all_sdrs(file_name):
    send_ipmitool_command("sdr", "dump", file_name)


#  read sensor value via ipmitool
def read_sensor_raw_value(sensor_num, event_type="threshold"):
    """
    Get sensor readying:
    - for analog sensor, return int
    - for discrete sensor, return 2 byte's hex, e.g. 0x1ac0
    :param sensor_num: sensor number
    :param event_type: "discrete" or "analog"
    :return:
    """

    result = send_ipmitool_command('raw', '0x04', '0x2d',
                                          hex(sensor_num))
    if result == -1:
        return 0
    if event_type == "threshold":
        value = result.split()[0]
        info = "sensor num: {0} value: 0x{1}".format(hex(sensor_num), value)
        logger.info(info)
        return int(value, 16)
    elif event_type == "discrete":
        value = '0x'+result.split()[2]+result.split()[3]
        info = "sensor num: {0} value: {1}".format(hex(sensor_num), value)
        logger.info(info)
        return value

def parse_sdrs():
    dump_all_sdrs(SDR_NAME)
    if os.path.isfile(SDR_NAME) == False:
        print "The file don't exist, Please double check!"
        sys.exit(1)

    fd = open(SDR_NAME, 'rb')
    file_size = os.path.getsize(SDR_NAME)
    offset = 0
    record_header_size = 5
    while offset < file_size:
        # get record type
        fd.seek(offset+3)
        record_type = ord(fd.read(1))

        # get record length
        fd.seek(offset+4)
        record_length = ord(fd.read(1))

        # we just care record type 0x1 and 0x2 right now
        if record_type != 0x1 and record_type != 0x2:
            offset += record_header_size + record_length
            continue

        # get mc address
        fd.seek(offset+5)
        mc = ord(fd.read(1))

        # get LUN
        fd.seek(offset+6)
        lun = ord(fd.read(1))

        # get sensor num
        fd.seek(offset+7)
        sensor_num = ord(fd.read(1))

        # get sensor capability
        fd.seek(offset+11)
        sensor_cap = ord(fd.read(1))

        # get sensor type
        fd.seek(offset+12)
        sensor_type = ord(fd.read(1))

        # get event type
        fd.seek(offset+13)
        event_type = ord(fd.read(1))

        if event_type == 0x0:
            sensor_value = None
        elif event_type == 0x1:
            sensor_value = read_sensor_raw_value(sensor_num, 'threshold')
        else:
            sensor_value = read_sensor_raw_value(sensor_num, "discrete")

        # get lower threshold mask(lower byte)
        fd.seek(offset+14)
        sensor_ltm_lb = ord(fd.read(1))

        # get lower threshold mask(upper byte)
        fd.seek(offset+15)
        sensor_ltm_ub = ord(fd.read(1))

        # get upper threshold mask(lower byte)
        fd.seek(offset+16)
        sensor_utm_lb = ord(fd.read(1))

        # get upper threshold mask(upper byte)
        fd.seek(offset+17)
        sensor_utm_ub = ord(fd.read(1))

        # settable threshold mask
        fd.seek(offset+18)
        sensor_rtm = ord(fd.read(1))

        # readable threshold mask
        fd.seek(offset+19)
        sensor_stm = ord(fd.read(1))

        # get sensor units 1 byte
        fd.seek(offset+20)
        sensor_su1 = ord(fd.read(1))

        # get sensor units 2 byte
        fd.seek(offset+21)
        sensor_su2 = ord(fd.read(1))

        sensor_name = ''
        sensor_obj = None
        # Full sensor record
        if record_type == 0x1:
            # get sensor name
            sensor_name_length = record_header_size + record_length - 48
            fd.seek(offset+48)
            for index in range(0, sensor_name_length):
                sensor_name += chr(ord(fd.read(1)))

            # build sensor
            sensor_obj = build_sensors(sensor_name,
                                       sensor_num,
                                       mc,
                                       sensor_value,
                                       sensor_type)

            # get sensor "M" value lower byte
            fd.seek(offset+24)
            sensor_m_lb = ord(fd.read(1))

            # get sensor "M" value upper byte
            fd.seek(offset+25)
            sensor_m_ub = ord(fd.read(1))

            # get sensor "B" value lower byte
            fd.seek(offset+26)
            sensor_b_lb = ord(fd.read(1))

            # get sensor "B" value upper byte
            fd.seek(offset+27)
            sensor_b_ub = ord(fd.read(1))

            # get Accuracy
            fd.seek(offset+28)
            sensor_acc = ord(fd.read(1))

            # get exp value
            fd.seek(offset+29)
            sensor_exp = ord(fd.read(1))

            #  set sensor "M" value lower byte
            sensor_obj.set_m_lb(sensor_m_lb)

            # set sensor "M" value upper byte
            sensor_obj.set_m_ub(sensor_m_ub)

            # set sensor "B" value lower byte
            sensor_obj.set_b_lb(sensor_b_lb)

            # set sensor "B" value upper byte
            sensor_obj.set_b_ub(sensor_b_ub)

            sensor_obj.set_accuracy(sensor_acc)

            # set exp value
            sensor_obj.set_exp(sensor_exp)

            # set threshold
            fd.seek(offset+36)
            sensor_obj.set_unr(ord(fd.read(1)))

            fd.seek(offset+37)
            sensor_obj.set_uc(ord(fd.read(1)))

            fd.seek(offset+38)
            sensor_obj.set_unc(ord(fd.read(1)))

            fd.seek(offset+39)
            sensor_obj.set_lnr(ord(fd.read(1)))

            fd.seek(offset+40)
            sensor_obj.set_lc(ord(fd.read(1)))

            fd.seek(offset+41)
            sensor_obj.set_lnc(ord(fd.read(1)))

            # output the sensor reading factor
            sensor_obj.get_reading_factor()
        # compact sensor record
        else:
            # get sensor name
            sensor_name_length = record_header_size + record_length - 32
            fd.seek(offset+32)
            for index in range(0, sensor_name_length):
                sensor_name += chr(ord(fd.read(1)))

            # build sensor
            sensor_obj = build_sensors(sensor_name,
                                       sensor_num,
                                       mc,
                                       sensor_value,
                                       sensor_type)

        # set mc address
        sensor_obj.set_mc(mc)

        # set lun
        sensor_obj.set_lun(lun)

        # set lower threshold (lower byte)
        sensor_obj.set_ltm_lb(sensor_ltm_lb)

        # set lower threshold (upper byte)
        sensor_obj.set_ltm_ub(sensor_ltm_ub)

        # set upper threshold (lower byte)
        sensor_obj.set_utm_lb(sensor_utm_lb)

        # set upper threshold (upper byte)
        sensor_obj.set_utm_ub(sensor_utm_ub)

        # set settable threshold mask
        sensor_obj.set_stm(sensor_stm)

        # set readable threshold mask
        sensor_obj.set_rtm(sensor_rtm)

        # set sensor units 1 byte
        sensor_obj.set_su1(sensor_su1)

        # Forrest comment this raw value out since we have
        # no clue how this sensor unit bit [7:6] impacts sensor
        # reading.

        # if sensor_su1 >> 6 != 0:
        #     raw_value = struct.unpack('b', chr(sensor_value))[0]
        #     sensor_obj.set_raw_value(raw_value)

        # set sensor units 2 byte
        sensor_obj.set_su2(sensor_su2)

        # set capability
        sensor_obj.set_cap(sensor_cap)

        # set event type
        sensor_obj.set_event_type(event_type)

        # initialize SEL for the sensor
        sensor_obj.initialize_sel()

        # move to next sensor
        offset = offset + record_length + record_header_size

    # delete temp file
    fd.close()
    os.remove(SDR_NAME)

'''
*********************************************************
Copyright @ 2018 Dell EMC Corporation All Rights Reserved
*********************************************************
'''
from infrasim.chassis.dataset import DataSet
from infrasim.chassis.share_memory import CShareMemory
import os
import struct


class Agent(object):

    def __init__(self):
        self.__shm = CShareMemory()
        self.__file = None

    def open(self, name):
        self.__file = self.__shm.open("share_mem_{}".format(name))

    def close(self):
        self.__shm.close()

    def __get_section(self, title):
        """
        find the section level by level
        :return <0: not found specified section.
        :return 0:  more sub sections.
        :return >0: the length of data
        """
        ids = title.split('/')
        self.__file.seek(0, os.SEEK_SET)
        ds = DataSet()
        for sub_title in ids:
            ret = ds.find_section(self.__file, sub_title)
            if ret is None:
                return -1
            self.__file.seek(ret[0], os.SEEK_CUR)
        if len(ds.get_header_list(self.__file)) == 0:
            return ret[1] - 4
        else:
            return 0

    def get(self, title):
        """
        return the content of section.
        :param title: full name of section.
        :return data: whole data of the section.
        """
        length = self.__get_section(title)
        if length > 0:
            return self.__file.read(length)
        else:
            return None

    def set(self, title, data):
        """
        change value of section.
        fail if data length exceeds the size.
        :param  title: full name of section will be modified.
        :param  data:  data will be saved.
        """
        length = self.__get_section(title)
        if length >= len(data):
            self.__file.write(data.encode())
            return True
        else:
            return False

    def __iterate_sections(self, length=0):
        ds = DataSet()
        start = self.__file.tell()
        headers = ds.get_header_list(self.__file)
        if len(headers) == 0:
            sub_len = length if length < 8 else 8
            # only read 8 bytes in max
            content = struct.unpack("{}s".format(sub_len), self.__file.read(sub_len))[0]
            content = content.rstrip('\0')
            return (length, content)

        ret = {}
        for header in headers:
            self.__file.seek(start + header[1], os.SEEK_SET)
            subs = self.__iterate_sections(header[2] - 4)
            ret[header[0]] = subs
        return ret

    def get_all_sections(self):
        """
        get the the dict of data sections.
        Only 8 bytes of data will be returnd.
        """
        self.__file.seek(0, os.SEEK_SET)
        return self.__iterate_sections()

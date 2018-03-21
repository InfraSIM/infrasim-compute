'''
*********************************************************
Copyright @ 2018 Dell EMC Corporation All Rights Reserved
*********************************************************
'''

import math
import struct


class DataSet(object):
    '''
    load data from different source.
    '''

    def __init__(self):
        self.__sections = {}
        self._fmt = "16sII"

    def export(self):
        '''
        save data to file.
        '''
        pass

    def append(self, key, data):
        self.__sections[key] = data

    def __get_length(self, data):
        length_dict = {}
        _total_len = 4

        if isinstance(data, str):
            _len = int(math.ceil(len(data) / 4.0) * 4)
            return [ _len, _len + _total_len ]

        for key in data.keys():
            length_dict[key] = self.__get_length(data[key])
            _total_len += length_dict[key][1]

        _total_len += struct.calcsize(self._fmt) * len(data)

        return [ length_dict, _total_len ]

    def write_bin_file(self, fo, data, length):
        if isinstance(data, str):
            fo.write(struct.pack("I", 0))
            fo.write(struct.pack("{}s".format(length[0]), data))

        else:
            length = length[0]
            fo.write(struct.pack("I", len(data)))
            offset = 4 + struct.calcsize(self._fmt) * len(data)
            for key in data.keys():
                _len = length[key][1]
                fo.write(struct.pack(self._fmt, key, offset, _len))
                offset += _len

            for key in data.keys():
                self.write_bin_file(fo, data[key], length[key])

    def save(self, filename):
        with open(filename, 'wb') as fo:
            self.write_bin_file(fo, self.__sections, self.__get_length(self.__sections))


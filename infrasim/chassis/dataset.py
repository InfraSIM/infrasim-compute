'''
*********************************************************
Copyright @ 2018 Dell EMC Corporation All Rights Reserved
*********************************************************
'''
import math
import struct


class DataSet(object):
    '''
    Save data into file
    '''

    def __init__(self):
        self.__sections = {}
        self._fmt = "16sII"  # title, offset_from_section_start, length_includes_leading_count

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
            return [_len, _len + _total_len]

        for key in data.keys():
            length_dict[key] = self.__get_length(data[key])
            _total_len += length_dict[key][1]

        _total_len += struct.calcsize(self._fmt) * len(data)

        return [length_dict, _total_len]

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

    def get_header_list(self, fi):
        ret = []
        count = struct.unpack("I", fi.read(4))[0]
        for _ in range(count):
            item = struct.unpack(self._fmt, fi.read(struct.calcsize(self._fmt)))
            ret.append((item[0].rstrip('\0'), item[1], item[2]))
        return ret

    def find_section(self, fi, title):
        items = self.get_header_list(fi)
        len_headers = 4 + struct.calcsize(self._fmt) * len(items)
        section = filter(lambda x: x[0] == title, items)
        if len(section) == 1:
            return (section[0][1] - len_headers, section[0][2])
        return None

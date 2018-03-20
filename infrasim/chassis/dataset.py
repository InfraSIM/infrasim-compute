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
        self.__sections = []
        self._fmt = "32sII"

    def fill(self, file_name):
        sections = self.__sections
        # get header size
        size = struct.calcsize(self._fmt) * len(sections)
        for section in sections:
            # pad data.
            section["length"] = int(math.ceil(len(section["data"]) / 4.0) * 4)
            size += section["length"]

        # plus space for count
        size += 4

        with open(file_name, 'wb') as fo:
            # write count of sections
            fo.write(struct.pack("I", len(sections)))
            header_offset = 4
            data_offset = struct.calcsize(self._fmt) * len(sections) + header_offset
            for section in sections:
                # write header item
                header = struct.pack(self._fmt, section["id"], data_offset, section["length"])
                fo.seek(header_offset)
                fo.write(header)
                header_offset += struct.calcsize(self._fmt)
                # write section
                fo.seek(data_offset)
                fo.write(section["data"])
                data_offset += section["length"]

    def export(self):
        '''
        save data to file.
        '''
        pass

    def append(self, id, data):
        self.__sections.append({'id':id, 'data':data})

    def get_length(self, sections):
        length = 0
        for item in sections:
            data = item["data"]
            if isinstance(data, list):
                item["length"] = self.get_length(data)
            else:
                item["length"] = int(math.ceil(len(data) / 4.0) * 4) + 4
            length += item["length"]
        # totoal_sub_length + header_size + count_space
        return (length + len(sections) * struct.calcsize(self._fmt) + 4)

    def fill_sections(self, fo, sections):
        # write count of sections
        fo.write(struct.pack("I", len(sections)))
        data_offset = struct.calcsize(self._fmt) * len(sections) + 4
        for section in sections:
            # write header item
            header = struct.pack(self._fmt, section["id"], data_offset, section["length"])
            fo.write(header)
            data_offset += section["length"]
        for section in sections:
            # write section
            data = section["data"]
            if isinstance(data, list):
                self.fill_sections(fo, data)
            else:
                fo.write(struct.pack("I", 0))
                fo.write(data)
                padding = section["length"] - 4 - len(data)
                if padding > 0:
                    # skip padding space.
                    fo.seek(padding, 1)

    def save(self, filename):
        size = self.get_length(self.__sections)
        with open(filename, 'wb') as fo:
            self.fill_sections(fo, self.__sections)


'''
*********************************************************
Copyright @ 2018 Dell EMC Corporation All Rights Reserved
*********************************************************
'''

import struct
import math

class DataSet(object):
    '''
    load data from different source.
    '''
    def __init__(self, name):
        self.__chassis_name = name
        self.__file = "file"
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
    
    def save(self):
        '''
        save data to file.
        '''
        pass

    def load(self):
        '''
        parse data from potential source and pack them into __sections
        '''
        self.__sections.append({'id':"test_id", 'data':"12345678".encode()})
        '''
        tmp = get_bios_data()
        if tmp:
            self.__section.append({'id':tmp.get_id(), 'data':tmp.get_data()})
        tmp = get_drive_data()
        if tmp:
            self.__section.append({'id':tmp.get_id(), 'data':tmp.get_data()})
        '''
    

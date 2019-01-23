'''
*********************************************************
Copyright @ 2018 Dell EMC Corporation All Rights Reserved
*********************************************************
This file contains the function to modify Emulation data.
Refer to Platform Management FRU Information Storage Definition V1.3
'''
import re


class FruCmd(object):
    """
    Decode FRU0 command and provide API to modify chassis data.
    """
    INTERNAL_USE_AREA = 1
    CHASSIS_INFO_AREA = 2
    BOARD_INFO_AREA = 3
    PRODUCT_INFO_AREA = 4
    MULTIRECORD_AREA = 5

    def __init__(self):
        self.fru_id = 0
        self.len = 0
        self.data = []
        self.file = None
        self._data_area = [None, None]
        self._changed = False

    def SetFruHeader(self, initial):
        sec = initial.split(" ")
        self.fru_id = int(sec[2], 16)
        self.len = int(sec[3], 16)

    def __str__(self):
        content = []
        if self.file:
            # save data to file
            if self._changed:
                with open(self.file, "wb") as f:
                    f.write(''.join([chr(x) for x in self.data]))
            content.append("mc_add_fru_data 0x20 {} {} file 0 \"{}\"".format(
                hex(self.fru_id), hex(self.len), self.file))
        else:
            content.append("mc_add_fru_data 0x20 {} {} data".format(hex(self.fru_id), hex(self.len)))
            for position in range(0, len(self.data), 8):
                content.append(" ".join("{:#04x}".format(x) for x in self.data[position:position + 8]))

        return " \\\n".join(content) + "\n"

    def AppendLine(self, line):
        values = [int(x, 16) for x in line.rstrip("\\\n").split(" ")[:-1]]
        self.data.extend(values)

    def LoadFromFile(self, src_file):
        self.file = src_file
        # load binary file.
        with open(src_file, "rb") as f:
            _data = f.read()
        self.data = [ord(x) for x in _data]

    def Decode(self):
        """
        Decode the FRU and extract sub data areas.
        return True if this fru contains chassis info.
        """
        if self.fru_id == 0 and self.len == 0:
            return False

        if self.data[0] == 0x01:
            # decode Common Header. Refer to FRM spec, chapter 8
            for index in range(FruCmd.CHASSIS_INFO_AREA, FruCmd.MULTIRECORD_AREA):
                offset = self.data[index] * 8
                if offset != 0:
                    end = offset + self.data[offset + 1] * 8
                    self._data_area.append({"start": offset, "end": end, "data": self.data[offset:end]})
                else:
                    self._data_area.append(None)

            # decode each record and get whold MultiRecord area
            offset = self.data[FruCmd.MULTIRECORD_AREA] * 8
            if offset != 0:
                end = offset
                while (self.data[end + 1] & 0x80) == 0:  # End_of_list is Zero.
                    # get length of current record.
                    record_length = self.data[end + 2]
                    # plus length of record header
                    end += record_length + 5
                self._data_area.append({"start": offset, "end": end, "data": self.data[offset:end]})
            else:
                self._data_area.append(None)

            # Split Internal Use Area because it may not comply with the spec and doesn't has length.
            # Take start position of next area as its end postion.
            internal_start = self.data[FruCmd.INTERNAL_USE_AREA] * 8

            if internal_start > 0:
                internal_stop = self.len
                for area in self._data_area[FruCmd.CHASSIS_INFO_AREA:FruCmd.MULTIRECORD_AREA + 1]:
                    if area and internal_start < area["start"] and internal_stop > area["start"]:
                        internal_stop = area["start"]
                self._data_area[FruCmd.INTERNAL_USE_AREA] = {
                    "start": internal_start, "end": internal_stop, "data": self.data[internal_start:internal_stop]}
            # return True if this fru contains chassis info.
            return self._data_area[FruCmd.CHASSIS_INFO_AREA] is not None
        return False

    def __decode_table(self, _data, _pos):
        values = []
        while _data[_pos] != 0xc1:  # 0xc1 means table end.
            _len = _data[_pos] & 0x3f
            values.append(_data[_pos: _pos + 1 + _len])
            _pos = _pos + 1 + _len
        return values

    def __pad_bytes(self, _data, num=4):
        _remain = len(_data) % num
        if _remain:
            _data.extend([0] * (num - _remain))

    def __change_str_value(self, values, idx, value):
        if value is None:
            return
        value = [ord(x) for x in value]
        self.__pad_bytes(value)
        if len(value) > 0x3c:
            value = value[:0x3c]
        # insert type/length field
        value.insert(0, 0xc0 + len(value))
        values[idx] = value

    def __fill_table(self, result, values):
        # compose data records
        for record in values:
            result.extend(record)
        # add END flag
        result.append(0xc1)

        # add empty slot for checksum.
        result.append(0)

        # pad empty space.
        self.__pad_bytes(result, 8)

        # fill length.
        result[1] = len(result) / 8

        # update checksum.
        result[-1] = (-sum(result)) & 0xff

    def ChangeChassisInfo(self, info):
        """
        Modify chassis information in Chassis Info Area of FRU
        """
        if info is None:
            return
        if self._data_area[FruCmd.CHASSIS_INFO_AREA] is None:
            return
        _data = self._data_area[FruCmd.CHASSIS_INFO_AREA]['data']
        # decode table from byte 3
        _ori_values = self.__decode_table(_data, 3)

        self.__change_str_value(_ori_values, 0, info.get('pn'))
        self.__change_str_value(_ori_values, 1, info.get('sn'))

        # Format Version = 0x01. Initial length = 0
        result = [0x01, 0x00]
        # Refer to SMBios spec Chap 7.4.1 System Enclosure or Chassis Types
        # Refer to EMC technical white paper in Dell Community, the Type is 0x17
        result.append(0x17)
        self.__fill_table(result, _ori_values)

        self._data_area[FruCmd.CHASSIS_INFO_AREA] = {"start": 0, "end": 0, "data": result}

    def ChangeBoardInfo(self, info):
        """
        Modify board information of FRU
        """
        if info is None:
            return
        if self._data_area[FruCmd.BOARD_INFO_AREA] is None:
            return
        _data = self._data_area[FruCmd.BOARD_INFO_AREA]['data']
        # decode table from byte 6
        _ori_values = self.__decode_table(_data, 6)

        self.__change_str_value(_ori_values, 0, info.get('manufacturer'))
        self.__change_str_value(_ori_values, 1, info.get('name'))
        self.__change_str_value(_ori_values, 2, info.get('sn'))
        self.__change_str_value(_ori_values, 3, info.get('pn'))

        # Format Version = 0x01. Initial length = 0
        result = _data[0:6]

        self.__fill_table(result, _ori_values)
        self._data_area[FruCmd.BOARD_INFO_AREA] = {"start": 0, "end": 0, "data": result}

    def ChangeProductInfo(self, info):
        """
        Modify product information of FRU
        """
        if info is None:
            return
        if self._data_area[FruCmd.PRODUCT_INFO_AREA] is None:
            return
        _data = self._data_area[FruCmd.PRODUCT_INFO_AREA]['data']
        # decode table from byte 3
        _ori_values = self.__decode_table(_data, 3)

        self.__change_str_value(_ori_values, 0, info.get('manufacturer'))
        self.__change_str_value(_ori_values, 1, info.get('name'))
        self.__change_str_value(_ori_values, 2, info.get('pn'))
        self.__change_str_value(_ori_values, 3, info.get('version'))
        self.__change_str_value(_ori_values, 4, info.get('sn'))

        # Format Version = 0x01. Initial length = 0
        result = _data[0:3]

        self.__fill_table(result, _ori_values)

        self._data_area[FruCmd.PRODUCT_INFO_AREA] = {"start": 0, "end": 0, "data": result}

    def UpdateData(self):
        # Adjust positon of all areas
        start = 8
        for index in (FruCmd.CHASSIS_INFO_AREA, FruCmd.BOARD_INFO_AREA, FruCmd.PRODUCT_INFO_AREA,
                      FruCmd.MULTIRECORD_AREA, FruCmd.INTERNAL_USE_AREA):
            area = self._data_area[index]
            if area:
                area["start"] = start
                end = area["start"] + len(area["data"])
                self.data[start:end] = area["data"]
                self.data[index] = area["start"] / 8
                area["end"] = end
                start = end
        # ensure the length doesn't exceed.
        if len(self.data) > self.len:
            self.data = self.data[:self.len]
        # update checksum of Entry Point
        self.data[7] = (-sum(self.data[0:8]) & 0xff)
        self._changed = True


class FruFile(object):
    """
    Fru file holds the all contents line by line.
    """

    def __init__(self, src_file):
        self._fru_cmds = []
        self._data = self.__load(src_file)

    def __load(self, src_file):
        data = []

        with open(src_file, "r") as fi:
            lines = fi.readlines()

        is_processing_fru = False
        fru_cmd = None
        file_re = re.compile(r'mc_add_fru_data 0x20 0x[a-fA-F0-9]+ 0x[a-fA-F0-9]+ file 0 \"(.*)\"')
        data_re = re.compile(r'mc_add_fru_data 0x20 0x[a-fA-F0-9]+ 0x[a-fA-F0-9]+ data')

        for line in lines:
            if is_processing_fru:
                fru_cmd.AppendLine(line)
                if not line.endswith("\\\n"):
                    is_processing_fru = False
            else:
                match_data = data_re.search(line)
                if match_data:
                    is_processing_fru = True
                    fru_cmd = FruCmd()
                    fru_cmd.SetFruHeader(line)
                    data.append(fru_cmd)
                    self._fru_cmds.append(fru_cmd)
                    # next process txt line
                    continue
                match_file = file_re.search(line)
                if match_file:
                    fru_file = match_file.group(1)
                    fru_cmd = FruCmd()
                    fru_cmd.SetFruHeader(line)
                    fru_cmd.LoadFromFile(fru_file)
                    data.append(fru_cmd)
                    self._fru_cmds.append(fru_cmd)
                    continue
                # add non-fru data.
                data.append(line)

        return data

    def ChangeChassisInfo(self, pn, sn):
        '''
        change chassis info for all FRU contains chassis.
        '''
        for fru_cmd in self._fru_cmds:
            if fru_cmd.Decode() is True:
                fru_cmd.ChangeChassisInfo({"pn": pn, "sn": sn})
                fru_cmd.UpdateData()

    def ChangeFruInfo(self, info_dict):
        '''
        change fru data.
        '''
        for fru_id, fru_data in info_dict.items():
            if isinstance(fru_id, str):
                fru_id = int(fru_id)
            for fru_cmd in self._fru_cmds:
                if fru_cmd.fru_id == fru_id:
                    fru_cmd.Decode()
                    fru_cmd.ChangeChassisInfo(fru_data.get('chassis'))
                    fru_cmd.ChangeBoardInfo(fru_data.get('board'))
                    fru_cmd.ChangeProductInfo(fru_data.get('product'))
                    fru_cmd.UpdateData()

    def Save(self, emu):
        with open(emu, "w") as fo:
            for item in self._data:
                fo.write(str(item))

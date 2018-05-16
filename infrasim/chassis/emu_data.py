'''
*********************************************************
Copyright @ 2018 Dell EMC Corporation All Rights Reserved
*********************************************************
This file contains the function to modify Emulation data.
Refer to Platform Management FRU Information Storage Definition V1.3
'''
import math
import struct


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
        self.type = 0
        self.len = 0
        self.data = []
        self._data_area = [None]

    def SetFruHeader(self, initial):
        sec = initial.split(" ")
        self.type = int(sec[2], 16)
        self.len = int(sec[3], 16)

    def __str__(self):
        content = []
        content.append("mc_add_fru_data 0x20 {} {} data".format(hex(self.type), hex(self.len)))
        for position in range(0, len(self.data), 8):
            content.append(" ".join("{:#04x}".format(x) for x in self.data[position:position + 8]))
        return " \\\n".join(content) + "\n"

    def AppendLine(self, line):
        values = [int(x, 16) for x in line.rstrip("\\\n").split(" ")[:-1]]
        self.data.extend(values)

    def Decode(self):
        """
        Decode the FRU0 and extract sub data areas.
        """
        if self.type == 0 and self.len == 0:
            return False
        if self.data[0] == 0x01:
            # decode Common Header. Refer to FRM spec, chapter 8
            for index in range(FruCmd.INTERNAL_USE_AREA, FruCmd.MULTIRECORD_AREA):
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
                while (self.data[end + 1] & 0x80) == 0:
                    # get length of current record.
                    record_length = self.data[end + 2]
                    if record_length == 0:
                        raise Exception("Wrong format of multi-record")
                    end += record_length
                # plus length of current record.
                end += 5
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
            return True
        return False

    def ChangeChassisInfo(self, pn, sn):
        """
        Modify chassis information in Chassis Info Area of FRU 0
        """
        # Chassis Type is 0x01.
        result = [0x01, 0x00]
        # Refer to SMBios spec Chap 7.4.1 System Enclosure or Chassis Types
        # Refer to EMC technical white paper in Dell Community, the Type is 0x17
        result.append(0x17)
        # update PN
        result.append(0xc0 + len(pn))
        result.extend([struct.unpack("B", x)[0] for x in pn])
        # update SN
        result.append(0xc0 + len(sn))
        result.extend([struct.unpack("B", x)[0] for x in sn])
        # add END flag
        result.append(0xc1)
        # calculate total size
        length = int(math.ceil(len(result) / 8.0) * 8)
        result[1] = length / 8
        # pad empty space.
        result.extend([0] * (length - len(result)))
        # update checksum.
        result[length - 1] = (-sum(result)) & 0xff

        self._data_area[FruCmd.CHASSIS_INFO_AREA] = {"start": 0, "end": 0, "data": result}

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
            del self.data[self.len:]
        # update checksum of Entry Point
        self.data[7] = (-sum(self.data[0:8]) & 0xff)


class FruFile(object):
    """
    Fru file holds the all contents line by line.
    """

    def __init__(self, src_file):
        self._fru0_cmd = None
        self._data = self.__load(src_file)

    def __load(self, src_file):
        data = []

        with open(src_file, "r") as fi:
            lines = fi.readlines()

        is_processing_fru = False
        fru_cmd = None
        for line in lines:
            if is_processing_fru:
                fru_cmd.AppendLine(line)
                if not line.endswith("\\\n"):
                    is_processing_fru = False
            elif str.startswith(line, "mc_add_fru_data 0x20 0x00"):
                # Get the Fru 0 (Builtin FRU Device) Data
                # Refer to Chapter 1, Chassis info should only be in baseboard.
                is_processing_fru = True
                fru_cmd = FruCmd()
                fru_cmd.SetFruHeader(line)
                data.append(fru_cmd)
                self._fru0_cmd = fru_cmd
            else:
                data.append(line)

        return data

    def ChangeChassisInfo(self, pn, sn):
        if self._fru0_cmd and self._fru0_cmd.Decode():
            self._fru0_cmd.ChangeChassisInfo(pn, sn)
            self._fru0_cmd.UpdateData()
        # print(str(self._fru0_cmd))

    def Save(self, emu):
        with open(emu, "w") as fo:
            for item in self._data:
                fo.write(str(item))

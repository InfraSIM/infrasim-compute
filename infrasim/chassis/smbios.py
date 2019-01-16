'''
*********************************************************
Copyright @ 2018 Dell EMC Corporation All Rights Reserved
*********************************************************
'''
import struct
import re


class SMBios(object):
    '''
    Decode smbios.bin and modify sn.

    Ref to SMBios SPEC Ver: 2.7.1,
    Chapter 5.2.1:
    struct SMBIOSEntryPoint {
     char EntryPointString[4];    //This is _SM_
     uchar Checksum;              //This value summed with all the values of the table, should be 0 (overflow)
     uchar Length;                //Length of the Entry Point Table. Since version 2.1 of SMBIOS, this is 0x1F
     uchar MajorVersion;          //Major Version of SMBIOS
     uchar MinorVersion;          //Minor Version of SMBIOS
     ushort MaxStructureSize;     //Maximum size of a SMBIOS Structure (we will se later)
     uchar EntryPointRevision;    //...
     char FormattedArea[5];       //...
     char EntryPointString2[5];   //This is _DMI_
     uchar Checksum2;             //Checksum for values from EntryPointString2 to the end of table
     ushort TableLength;          //Length of the Table containing all the structures
     uint TableAddress;         //Address of the Table
     ushort NumberOfStructures;   //Number of structures in the table
     uchar BCDRevision;           //Unused
     uchar pad;                   //pad.
    };

    Chapter 6.1.2:
    struct SMBIOSHeader {
     uchar Type;
     uchar Length;
     ushort Handle;
    };
    '''
    _fmt_entry = "4sBBBBHb5s5sBHIHBB"
    '''
    spec filename: DSP0134_3.0.0.pdf
    Entry Format 3.0. Ref to SMBios SPEC Ver:3.0.0, Chapter:5.2.2
    struct SMBIOSEntryPoint {
     char EntryPointString[5];    //This is '_SM3_'
     uchar Checksum;              //This value summed with all the values of the table, should be 0 (overflow)
     uchar Length;                //Length of the Entry Point Table. this is 0x18 in spec 3.0
     uchar MajorVersion;          //Major Version of SMBIOS
     uchar MinorVersion;          //Minor Version of SMBIOS
     uchar docrev;                //docrev
     uchar entry_point_rev;       //01h in spec 3.
     uchar reserved;              //Address of the Table
     ulong MaxSizeOfStructures;   //Max size of the table
     uint64_t TableAddress;       //offset of all tables.
    };
    '''
    _fmt3_entry = "5sBBBBBBBIQ"
    _fmt_header = "BBH"
    Id_Checksum = 1
    Id_MaxStructureSize = 5
    Id_Checksum2 = 9
    Id_TotalLength = 10
    Id_TableAddress = 11
    Id_NumberOfStructures = 12
    TYPE_SystemInformation = 1
    TYPE_BaseboardInformation = 2
    TYPE_ChassisInformation = 3
    TYPE_ProcessorInformation = 4
    TYPE_PhysicalMemoryArrayInformation = 16
    TYPE_MemoryDevice = 17

    def __init__(self, src):
        '''
        Open src file and decode it.
        '''
        self.__dict = []
        self.__entry = None
        self.__type1_index = None
        self.__type3_index = None
        self.__type4_index_list = []
        self.__type16_index_list = []
        self.__type17_index_list = []
        self.save = None
        with open(src, "rb") as fin:
            self._buf = fin.read()
        if self.__decode() is False and self.__decode3() is False:
            raise Exception("can't identify bios version")

    def __decode3(self):
        # unpack Entry Table
        entry = struct.unpack_from(SMBios._fmt3_entry, self._buf, 0)
        if not (entry[0] == "_SM3_" and entry[3] == 3):
            return False
        self.save = self.__save3
        self.__entry = entry
        # get offset from header['TableAddress'].
        offset = entry[9]
        while offset < len(self._buf):
            offset = self.__decode_entry(offset)
        return True

    def __save3(self, dst):
        # update "Structure table maximum size"
        entry = list(self.__entry)
        size = sum(map(lambda x: len(x), self.__dict))
        entry[8] = size

        # update checksum
        entry[SMBios.Id_Checksum] = 0
        entry[SMBios.Id_Checksum] = self.__get_checksum(struct.pack(SMBios._fmt3_entry, *entry))

        # calculate pad between header and tables.
        offset = entry[9]
        pad = offset - struct.calcsize(SMBios._fmt3_entry)
        # write file.
        with open(dst, "wb") as fo:
            fo.write(struct.pack(SMBios._fmt3_entry, *entry))
            fo.write('\0' * pad)
            for item in self.__dict:
                fo.write(item)

    def __decode(self):
        """
        Decode the SMBIOSEntryPoint
        """
        # unpack Entry Table
        entry = struct.unpack_from(SMBios._fmt_entry, self._buf, 0)
        if not (entry[0] == "_SM_"):
            return False
        self.save = self.__save
        self.__entry = entry
        offset = struct.calcsize(SMBios._fmt_entry)
        for _ in range(0, entry[12]):
            offset = self.__decode_entry(offset)
        return True

    def __decode_entry(self, offset):
        header = struct.unpack_from(SMBios._fmt_header, self._buf, offset)
        start = offset
        offset += header[1]
        while self._buf[offset] != '\0' or self._buf[offset + 1] != '\0':
            offset += 1
        offset += 2
        structure = self._buf[start:offset]

        if header[0] == SMBios.TYPE_SystemInformation:  # mark the system information structure.
            self.__type1_index = len(self.__dict)
        if header[0] == SMBios.TYPE_ChassisInformation:
            self.__type3_index = len(self.__dict)
        if header[0] == SMBios.TYPE_BaseboardInformation:
            self.__type2_index = len(self.__dict)
        if header[0] == SMBios.TYPE_ProcessorInformation:
            self.__type4_index_list.append(len(self.__dict))
        if header[0] == SMBios.TYPE_PhysicalMemoryArrayInformation:
            self.__type16_index_list.append(len(self.__dict))
        if header[0] == SMBios.TYPE_MemoryDevice:
            self.__type17_index_list.append(len(self.__dict))

        self.__dict.append(structure)
        return offset

    def __update_string(self, string_values, index, value):
        if value is None:
            return index
        if index <= 0:
            string_values.append(value)
            index = len(string_values)
        else:
            string_values[index - 1] = value
        return index

    def ModifyType1SystemInformation(self, info_map):
        '''
        support following fields,
        sn, uuid, and sku_number,
        '''
        if self.__type1_index is None:
            return
        # Refer to Chapter 7.2
        sys_info_fmt = "BBHBBBB16sBBB"
        # fetch the System Information Structure
        sys_info = self.__dict[self.__type1_index]
        # __decode header.
        info = list(struct.unpack_from(sys_info_fmt, sys_info))
        offset = struct.calcsize(sys_info_fmt)
        # split content
        string_values = sys_info[offset:].split('\0')

        # modify SN string.
        info[6] = self.__update_string(string_values, info[6], info_map.get('sn'))

        # modify uuid
        if 'uuid'in info_map and len(info_map['uuid']) == 16:
            info[7] = info_map['uuid']

        # modify SKU number
        sku_index = info[9]
        info[9] = self.__update_string(string_values, sku_index, info_map.get('sku_number'))

        # pack modified data and save it
        result = struct.pack(sys_info_fmt, *info)
        result += '\0'.join(string_values)
        self.__dict[self.__type1_index] = result

    def ModifyType2BaseboardInformation(self, info_map):
        if self.__type2_index is None:
            return
        # Ref to SMBios SPEC Ver: 2.7.1, Chapter 7.3
        board_info_fmt = "=BBHBBBBBBBHBB"
        board_info = self.__dict[self.__type2_index]
        info = list(struct.unpack_from(board_info_fmt, board_info))
        string_offset = struct.calcsize(board_info_fmt) + info[12] * 2
        # split string content
        string_values = board_info[string_offset:].split('\0')
        # Modify SN
        info[6] = self.__update_string(string_values, info[6], info_map.get('sn'))
        # Modify string of Location in Chassis
        location_index = info[9]
        info[9] = self.__update_string(string_values, location_index, info_map.get('location'))

        # pack modified data and save it
        result = struct.pack(board_info_fmt, *info)
        result += board_info[struct.calcsize(board_info_fmt):string_offset]
        result += '\0'.join(string_values)

        self.__dict[self.__type2_index] = result

    def ModifyType3ChassisInformation(self, info_map):
        '''
        support following fields,
        sn,
        '''
        if self.__type3_index is None:
            return
        # Ref to SMBios SPEC Ver: 2.7.1, Chapter 7.4
        # '=' force byte alignemnt.
        chassis_info_fmt = "=BBHBBBBBBBBBIBBBB"
        # fetch the System Information Structure
        chassis_info = self.__dict[self.__type3_index]
        # decode header.
        info = list(struct.unpack_from(chassis_info_fmt, chassis_info))
        # skip Contained elements start at 0x15h.
        offset = struct.calcsize(chassis_info_fmt) + info[15] * info[16] + 1
        # split string content
        string_values = chassis_info[offset:].split('\0')

        # modify SN string.
        sn_index = info[6]  # position number of SN.
        info[6] = self.__update_string(string_values, sn_index, info_map.get('sn'))

        # pack modified data and save it
        result = struct.pack(chassis_info_fmt, *info)
        result += chassis_info[struct.calcsize(chassis_info_fmt):offset]
        result += '\0'.join(string_values)

        self.__dict[self.__type3_index] = result

    def ModifyType4ProcessorInformation(self, cpu):
        '''
        support following fields,
        sn, version, core number, speed, max speed, part number and asset tag.
        '''
        if len(self.__type4_index_list) == 0:
            return
        # Format of Processor Information (Type 4). Ref Chapter 7.5
        pro_info_fmt = '=BBHBBBBQBBHHHBBHHHBBBBBBHHHHH'
        for idx in self.__type4_index_list:
            info = self.__dict[idx]
            pro_info = list(struct.unpack_from(pro_info_fmt, info))
            offset = struct.calcsize(pro_info_fmt)
            string_values = info[offset:].split('\0')

            # pro_info[7] = 0 # process ID
            # update Processor Version
            pro_info[8] = self.__update_string(string_values, pro_info[8], cpu.get("version"))
            pro_info[11] = cpu.get('max_speed', 4000)  # max spped. MHz
            pro_info[12] = cpu.get('speed', 1800)  # current speed. MHz

            # update sn
            pro_info[18] = self.__update_string(string_values, pro_info[18], cpu.get('sn'))
            # update asset tag
            pro_info[19] = self.__update_string(string_values, pro_info[19], cpu.get('asset_tag'))
            # update part number
            pro_info[20] = self.__update_string(string_values, pro_info[20], cpu.get('part_number'))

            core_number = cpu.get("cores", 4)
            pro_info[21] = core_number  # Core Count
            pro_info[22] = core_number  # Core Enabled
            pro_info[23] = core_number  # Thread Count
            # Core count 2, Core Enabled 2 and Thread Count 2 set to same value if core count < 255.
            pro_info[26] = core_number  # Core Count 2.
            pro_info[27] = core_number  # Core Enabled 2
            pro_info[28] = core_number  # Thread Count 2

            # pack modified data and save it
            result = struct.pack(pro_info_fmt, *pro_info)
            result += '\0'.join(string_values)
            self.__dict[idx] = result

    def CheckType16PhysicalMemoryArray(self, total_count):
        if len(self.__type16_index_list) == 0:
            raise Exception("Type 16 - Physical Memory Array is missing")
        fmt = '=BBHBBBIHHQ'
        count = 0
        for idx in self.__type16_index_list:
            raw = self.__dict[idx]
            info = struct.unpack_from(fmt, raw)
            # support there is 24 memory slots on board.
            # if not, Slot number in Type16 Physical Memory Array must be modified.
            # 8th field "Number of Memory Devices"
            count += info[8]
        if count < total_count:
            raise Exception('Not enough dimm slots. Provides: {}, expected: {}'.format(count, total_count))

    def ModifyType17MemoryDevice(self, dimm=None):
        '''
        support following fields,
        sn, size, part number, manufactuer, asset tag, part number and number of dimm
        '''
        self.CheckType16PhysicalMemoryArray(len(dimm))
        if len(self.__type4_index_list) == 0:
            raise Exception("Type 17 - Memory Device is missing")

        mem_info_fmt = '=BBHHHHHHBBBBBHHBBBBBIHHHH'
        if dimm is None:
            # don't modify memory device array.
            return

        class mem_dev_struct(list):
            fields = [
                "type",
                "length",
                "handle",
                "physical memory array handle",
                "memory error information handle",
                "total width",
                "data width",
                "size",
                "form factor",
                "device set",
                "device locator",
                "ban locator",
                "memory type",
                "type detail",
                "speed",
                "manufactuer",
                "sn",
                "asset tag",
                "part number",
                "attributes",
                "extended size",
                "configured memory clock speed",
                "min volt",
                "max volt",
                "config volt"]

            def __setitem__(self, key, value):
                super(mem_dev_struct, self).__setitem__(self.fields.index(key), value)

            def __getitem__(self, key):
                return super(mem_dev_struct, self).__getitem__(self.fields.index(key))

        dim_position_reg = re.compile(r'DIMM (\d+)')

        for idx in self.__type17_index_list:
            mem_info = self.__dict[idx]
            info = mem_dev_struct(struct.unpack_from(mem_info_fmt, mem_info))
            offset = struct.calcsize(mem_info_fmt)
            string_values = mem_info[offset:].split('\0')

            # found memory device by device locator
            # since the memory device array is not ordered.
            dev_locator = string_values[info["device locator"] - 1]
            m = dim_position_reg.match(dev_locator)
            if m:
                position = int(m.group(1))
            else:
                raise Exception('Can not found positon of memory device {0}'.format(dev_locator))
            # get expected dimm information.
            if position < len(dimm):
                dimm_info = dimm[position]
            else:
                # no dimm information.
                dimm_info = {}

            # modify memory device by dimm_info
            if dimm_info.get('size', 0) == 0:
                info["total width"] = 0
                info["data width"] = 0
                info["size"] = 0
                info["form factor"] = 2
                info["device set"] = 0
                info["device locator"] = 1
                info["ban locator"] = 2
                info["memory type"] = 2
                info["type detail"] = 0
                info["speed"] = 0
                info["attributes"] = 0
                info["extended size"] = 0
                info["configured memory clock speed"] = 0

                info["manufactuer"] = self.__update_string(string_values, info["manufactuer"], "NO DIMM")
                info["sn"] = self.__update_string(string_values, info["sn"], "NO DIMM")
                info["asset tag"] = self.__update_string(string_values, info["asset tag"], "NO DIMM")
                info["part number"] = self.__update_string(string_values, info["part number"], "NO DIMM")
            else:
                info["total width"] = 72
                info["data width"] = 64
                size = dimm_info.get('size')
                # according to spec,
                # info['size'] & 0x8000 == 1, unit = KB.
                # info['size'] & 0x8000 == 0, unit = MB.
                if size < 1024 * 1024:
                    size = size / 1024
                    info["size"] = 0x8000 + size
                else:
                    size = size / 1024 / 1024
                    info["size"] = size
                info["form factor"] = 9
                info["device set"] = 0
                info["device locator"] = 1
                info["ban locator"] = 2
                info["memory type"] = 26
                info["type detail"] = 128
                info["speed"] = 2666
                info["attributes"] = 2
                info["extended size"] = 0
                info["configured memory clock speed"] = 2666
                info["manufactuer"] = self.__update_string(string_values, info["manufactuer"],
                                                           dimm_info.get('manufactuer', 'Hynix'))
                info["sn"] = self.__update_string(string_values, info["sn"], dimm_info.get('sn'))
                info["asset tag"] = self.__update_string(string_values, info["asset tag"],
                                                         dimm_info.get('asset_tag', string_values[0] + '_AssetTag'))
                info["part number"] = self.__update_string(string_values, info["part number"],
                                                           dimm_info.get('part_number', 'HMA82GR7AFR8N-VK'))

            # pack modified data and save it
            result = struct.pack(mem_info_fmt, *info)
            result += '\0'.join(string_values)

            self.__dict[idx] = result

    def __get_checksum(self, buf):
        check_sum = sum(bytearray(buf))
        return (-check_sum) & 0xff

    def __save(self, dst):
        # check the MaxStructureSize in Entry.
        # update TableLength in Entry
        entry = list(self.__entry)
        size = 0
        for item in self.__dict:
            length = len(item)
            if length > entry[SMBios.Id_MaxStructureSize]:
                entry[SMBios.Id_MaxStructureSize] = length
            size += length
        entry[SMBios.Id_TotalLength] = size

        # update checksum
        entry[SMBios.Id_Checksum2] = 0
        entry[SMBios.Id_Checksum] = 0

        entry[SMBios.Id_Checksum2] = self.__get_checksum(struct.pack(SMBios._fmt_entry, *entry)[0x10:0xf])
        entry[SMBios.Id_Checksum] = self.__get_checksum(struct.pack(SMBios._fmt_entry, *entry))

        # write file.
        with open(dst, "wb") as fo:
            fo.write(struct.pack(SMBios._fmt_entry, *entry))
            for item in self.__dict:
                fo.write(item)

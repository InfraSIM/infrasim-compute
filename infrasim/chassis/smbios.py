'''
*********************************************************
Copyright @ 2018 Dell EMC Corporation All Rights Reserved
*********************************************************
'''
import struct


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

    def __init__(self, src):
        '''
        Open src file and decode it.
        '''
        self.__dict = []
        self.__entry = None
        self.__type1_index = None
        self.__type3_index = None
        with open(src, "rb") as fin:
            self._buf = fin.read()
            self.__decode()

    def __decode(self):
        """
        Decode the SMBIOSEntryPoint
        """
        # unpack Entry Table
        entry = struct.unpack_from(SMBios._fmt_entry, self._buf, 0)
        self.__entry = entry

        offset = struct.calcsize(SMBios._fmt_entry)
        for _ in range(0, entry[12]):
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

            self.__dict.append(structure)

    def ModifyType1SystemInformation(self, sn):
        if self.__type1_index is None:
            return
        # Refer to Chapter 7.2
        sys_info_fmt = "BBHBBBB16sBBB"
        # fetch the System Information Structure
        sys_info = self.__dict[self.__type1_index]
        # __decode header.
        info = struct.unpack_from(sys_info_fmt, sys_info)
        offset = struct.calcsize(sys_info_fmt)
        # split content
        string_values = sys_info[offset:].split('\0')

        # modify SN string.
        sn_index = info[6]  # position number of SN.
        if sn_index > 0:
            string_values[sn_index - 1] = sn
        else:
            info[6] = len(string_values) + 1
            string_values.append(sn)

        # pack modified data and save it
        result = struct.pack(sys_info_fmt, *info)
        result += '\0'.join(string_values)
        self.__dict[self.__type1_index] = result

    def ModifyType2BaseboardInformation(self, location):
        if self.__type2_index is None:
            return
        # Ref to SMBios SPEC Ver: 2.7.1, Chapter 7.3
        board_info_fmt = "=BBHBBBBBBBHBB"
        board_info = self.__dict[self.__type2_index]
        info = struct.unpack_from(board_info_fmt, board_info)
        string_offset = struct.calcsize(board_info_fmt) + info[12] * 2
        # split string content
        string_values = board_info[string_offset:].split('\0')
        # Modify string of Location in Chassis
        location_index = info[9]
        if location_index > 0:
            string_values[location_index - 1] = location
        else:
            info[9] = len(string_values) + 1
            string_values.append(location)

        # pack modified data and save it
        result = struct.pack(board_info_fmt, *info)
        result += board_info[struct.calcsize(board_info_fmt):string_offset]
        result += '\0'.join(string_values)

        self.__dict[self.__type2_index] = result

    def ModifyType3ChassisInformation(self, sn):
        if self.__type3_index is None:
            return
        # Ref to SMBios SPEC Ver: 2.7.1, Chapter 7.4
        # '=' force byte alignemnt.
        chassis_info_fmt = "=BBHBBBBBBBBBIBBBB"
        # fetch the System Information Structure
        chassis_info = self.__dict[self.__type3_index]
        # decode header.
        info = struct.unpack_from(chassis_info_fmt, chassis_info)
        # skip Contained elements start at 0x15h.
        offset = struct.calcsize(chassis_info_fmt) + info[15] * info[16] + 1
        # split string content
        string_values = chassis_info[offset:].split('\0')

        # modify SN string.
        sn_index = info[6]  # position number of SN.
        if sn_index > 0:
            string_values[sn_index - 1] = sn
        else:
            info[6] = len(string_values) + 1
            string_values.append(sn)

        # pack modified data and save it
        result = struct.pack(chassis_info_fmt, *info)
        result += chassis_info[struct.calcsize(chassis_info_fmt):offset]
        result += '\0'.join(string_values)

        self.__dict[self.__type3_index] = result

    def __get_checksum(self, buf):
        check_sum = sum(bytearray(buf))
        return (-check_sum) & 0xff

    def save(self, dst):
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

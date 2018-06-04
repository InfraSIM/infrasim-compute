'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


from infrasim.model.elements.drive_ide import IDEDrive


class IDECdrom(IDEDrive):
    def __init__(self, cdrom_info):
        # ISO should be raw format, force its format to 'raw'
        cdrom_info['format'] = 'raw'
        super(IDECdrom, self).__init__(cdrom_info)
        self._name = "ide-cd"

    def init(self):
        super(IDEDrive, self).init()

    def handle_parms(self):
        super(IDECdrom, self).handle_parms()
        print self.get_option()
